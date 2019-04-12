import json
import os
import pickle
import time

from bot_trading.bots.eva.fast_portfolio import FastPortfolio, TickNotAvailableException
from bot_trading.core.configuration import INITIAL_AMOUNT, TARGET_CURRENCY
from bot_trading.trading.fund import Fund
from bot_trading.trading.price_snapshot import PriceSnapshot
import numpy as np

POPULATION_SIZE = 100
CHECKPOINT_FILE = "trained_models/eva_population.bin"


def optimize(bot, snapshot: PriceSnapshot, start_hours_ago: float, run_length_hours: float):
    prices = index_prices(snapshot, start_hours_ago)
    optimize_with_samples(bot, prices, run_length_hours, snapshot)


def optimize_with_samples(bot, samples, run_length_hours, snapshot):
    bot.eva_initialization(snapshot)
    parameters = bot.get_parameters()
    population = get_population(parameters)
    run_length = int(3600 * run_length_hours / samples["meta"]["period_in_seconds"])
    sample_count = len(list(samples["data"].values())[0])
    last_save = 0
    epoch = 0
    while True:
        epoch += 1
        run_start = 0
        # plot_performance(bot, population)
        while True:
            if time.time() - last_save > 300:
                save_checkpoint(population)
                last_save = time.time()

            run_end = run_start + run_length
            if run_end > sample_count:
                print(f"EPOCH {epoch}")
                break

            try:
                evaluate_population(bot, population, samples, run_start, run_end)
            except TickNotAvailableException as e:
                run_start += e.missing_tick
                continue

            evolve(bot, population)

            run_start += run_length // 4


def plot_performance(bot, population):
    activate(bot, get_oldest_individual(population))
    bot.plot()


def get_oldest_individual(population):
    return max(sorted(population, key=lambda i: i["fitness"], reverse=True), key=lambda i: i["age"])


def get_best_individual(population):
    return max(population, key=lambda i: i["fitness"])


def evaluate_population(bot, population, samples, run_start, run_end):
    portfolio = FastPortfolio(samples, INITIAL_AMOUNT, TARGET_CURRENCY)
    portfolio.set_tick(run_start)

    buy_chunk = INITIAL_AMOUNT / len(portfolio.non_target_currencies)
    for currency in portfolio.non_target_currencies:
        if np.random.uniform() < 0.3:
            portfolio.request_transfer(Fund(buy_chunk, TARGET_CURRENCY), currency)

    print("EVALUATION STARTS")
    for individual in population:
        evaluate(bot, individual, portfolio.get_copy(), run_start, run_end)

    print(f"EVALUATION COMPLETE ({run_start}, {run_end})")


def evaluate(bot, individual, portfolio, run_start, run_end):
    activate(bot, individual)

    step_tick_count = int(bot.update_interval / portfolio._tick_duration)
    initial_value = portfolio.total_value
    portfolio.set_tick(run_end - 1)
    passive_final_value = portfolio.total_value

    for i in range(run_start, run_end, step_tick_count):
        portfolio.set_tick(i)
        bot.update_portfolio(portfolio)

    final_value = portfolio.total_value
    passive_update = passive_final_value - initial_value
    fitness_update = final_value - max(passive_final_value, initial_value) - 0.1
    individual["fitness"] += fitness_update
    individual["age"] += 1
    print(f"\t PASSIV {passive_update}")
    print(f"\t UPDATE {fitness_update}")
    print(f"\t AGE: {individual['age']}")
    print(f"TOTAL: {individual['fitness']}")


def fast_backtest(bot, samples):
    portfolio = FastPortfolio(samples, INITIAL_AMOUNT, TARGET_CURRENCY)
    portfolio.set_tick(0)
    bot.initialize(portfolio)

    step_tick_count = int(bot.update_interval / portfolio._tick_duration)
    end_index = len(next(iter(samples["data"].values())))

    print("FAST BACKTEST STARTS")
    i = 0
    while i < end_index:
        try:
            portfolio.set_tick(i)
            bot.update_portfolio(portfolio)
            i += step_tick_count
        except TickNotAvailableException as e:
            i += e.missing_tick
        #except IndexError:
        #    print("Index error stopping")
        #    break

    print(f"FINAL VALUE {portfolio.total_value} {TARGET_CURRENCY}")
    print(f"POSITIONS: {portfolio._positions}")


def activate(bot, individual):
    bot.set_parameters(individual["parameters"])


def evolve(bot, population):
    for i in reversed(range(len(population))):
        individual = population[i]
        if individual["fitness"] < 0:
            # kill the poor individual
            population.pop(i)

    if len(population) == POPULATION_SIZE:
        # decimation
        for _ in range(POPULATION_SIZE // 20):
            weakest = min(range(len(population)), key=lambda i: population[i]["fitness"])
            population.pop(weakest)

    while len(population) < POPULATION_SIZE / 2:
        population.append(create_individual(bot.get_parameters()))

    while len(population) < POPULATION_SIZE:
        parent1 = get_weighted_sample(population)
        parent2 = get_weighted_sample(population)

        child = produce_child(parent1, parent2)
        population.append(child)


def produce_child(parent1, parent2):
    new_parameters = []
    for p1, p2 in zip(parent1["parameters"], parent2["parameters"]):
        # combination_mask = np.random.uniform(0, 1.0)
        # combination_mask = (np.sign(np.random.standard_normal(size=p1.size)) + 1) / 2
        # combination_mask = (np.cumprod(np.sign(np.random.normal(,p1.shape) + 0.95)) + 1) / 2
        combination_operator = np.reshape(
            (np.cumprod(np.sign((np.random.binomial(1, 0.9, size=p1.size) - 0.5))) + 1) / 2,
            p1.shape)

        mutation_mask = np.random.binomial(1, 0.01, size=p1.shape)
        mutation_operator = np.random.standard_normal(p1.shape) * mutation_mask / 1000
        p = mutation_operator + p1 * combination_operator + p2 * (1.0 - combination_operator)
        new_parameters.append(p)

    parent1["fitness"] /= 2
    parent2["fitness"] /= 2
    return {
        "fitness": parent1["fitness"] + parent2["fitness"],
        "parameters": new_parameters,
        "age": 0
    }


def get_weighted_sample(population):
    weights = [i["fitness"] for i in population]
    p = np.array(weights) / np.sum(weights)
    return np.random.choice(population, p=p)


def get_population(parameters):
    population = load_checkpoint()
    if population:
        return population

    population = []
    for i in range(POPULATION_SIZE):
        individual = create_individual(parameters, keep_parameters=i == 0)

        population.append(individual)

    return population


def create_individual(parameters, keep_parameters=False):
    individual_parameters = []
    individual = {
        'parameters': individual_parameters,
        'fitness': 10.0,
        'age': 0
    }
    for parameter in parameters:
        if keep_parameters:
            individual_parameters.append(parameter * (1 + np.random.standard_normal(parameter.shape) / 1000))
        else:
            individual_parameters.append(np.random.uniform(size=parameter.shape))

    return individual


def index_prices(snapshot, start_hours_ago):
    training_start = snapshot.get_snapshot(seconds_back=start_hours_ago * 3600)

    currencies = list(snapshot.non_target_currencies)
    currency_samples = {}
    for currency in currencies:
        samples = training_start.get_unit_bid_ask_samples(currency, TICK_DURATION)
        currency_samples[currency] = samples

    return currency_samples


def save_checkpoint(population):
    # serialized = json.dumps(population, cls=NumpyEncoder)
    serialized = pickle.dumps(population)
    with open(CHECKPOINT_FILE, "wb") as f:
        f.write(serialized)


def load_checkpoint():
    if not os.path.exists(CHECKPOINT_FILE):
        return None

    with open(CHECKPOINT_FILE, "rb") as f:
        # population = json.load(f)
        population = pickle.load(f)

    for individual in population:
        if "age" not in individual:
            individual["age"] = 0

    return population


def load_samples(sample_file):
    if not os.path.exists(sample_file):
        return None

    with open(sample_file, "rb") as f:
        return pickle.load(f)


def save_samples(sample_file, samples):
    serialized = pickle.dumps(samples)
    with open(sample_file, "wb") as f:
        f.write(serialized)


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
