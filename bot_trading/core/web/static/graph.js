var SKIPPED_GRAPHS = {};
var SKIPPED_PORTFOLIO_GRAPHS = {};

document.addEventListener("visibilitychange", function () {
    if (document.visibilityState != "visible" && document.visibilityState != "prerender")
        return;

    var graphs = SKIPPED_GRAPHS;
    SKIPPED_GRAPHS = {};

    var portfolio_graphs = SKIPPED_PORTFOLIO_GRAPHS;
    SKIPPED_PORTFOLIO_GRAPHS = {}

    for (var slot in graphs) {
        showGraph(slot, graphs[slot]);
    }

    for (var slot in portfolio_graphs) {
        showPortfolioValuesGraph(slot, portfolio_graphs[slot]);
    }
});


function showPortfolioValuesGraph(slot, json) {
    if (document.visibilityState == "hidden") {
        SKIPPED_PORTFOLIO_GRAPHS[slot] = json;
        return;
    }
    var odata = json;

    var labels = [];
    var data = [];
    var minY = null;
    var maxY = null;
    for (var username in odata) {
        labels.push(username);

        ldata = []
        data.push(ldata);
        for (var entry of odata[username]) {
            var date = new Date(entry[0] * 1000);
            var value = entry[1];
            ldata.push({
                value: value,
                date: date
            });

            if (minY == null || minY > value) {
                minY = value;
            }

            if (maxY == null || maxY < value) {
                maxY = value;
            }
        }
    }

    var selector = '#' + slot;
    MG.data_graphic({
        title: "Portfolio Values",
        yax_format: function (v) {
            return "" + v
        },
        data: data,
        full_width: true,
        height: 600,
        right: 40,
        area: false,
        interpolate: d3.curveLinear,
        target: selector,
        show_secondary_x_label: false,
        show_confidence_band: ['l', 'u'],
        x_extended_ticks: true,
        y_extended_ticks: true,
        min_y_from_data: true,
        max_y: maxY,
        min_y: minY,
        transition_on_update: false,
        legend: labels,
        brush: 'xy'
    });
}

function showGraph(slot, json) {
    if (document.visibilityState == "hidden") {
        SKIPPED_GRAPHS[slot] = json;
        return;
    }

    var pair = json["pair"];
    var odata = json["data"];
    var omarkers = json["markers"];

    var data = [];
    var markers = [];
    var minY = null;
    var maxY = null;
    for (var i in odata) {
        o = odata[i];
        data.push({
            date: new Date(o["d"] * 1000),
            u: o["u"],
            l: o["l"],
            value: (o["u"] + o["l"]) / 2
        })

        if (minY == null || minY > o["l"])
            minY = o["l"];

        if (maxY == null || maxY < o["u"])
            maxY = o["u"];
    }

    for (var m of omarkers) {
        var mclass = m["b"] ? "buy" : "sell";
        markers.push({
            date: new Date(m["t"] * 1000),
            label: m["u"].trunc(15),
            lineclass: mclass,
            textclass: mclass
        });
    }

    var selector = '#' + slot;
    $(selector).click(function () {
        window.location = "/live_graph/" + pair;
    }).css('cursor', 'pointer');

    MG.data_graphic({
        title: pair + " spread history",
        data: data,
        yax_format: function (v) {
            return "" + v
        },
        full_width: true,
        height: 400,
        right: 40,
        area: false,
        interpolate: d3.curveLinear,
        target: selector,
        show_secondary_x_label: false,
        show_confidence_band: ['l', 'u'],
        x_extended_ticks: true,
        y_extended_ticks: true,
        min_y_from_data: true,
        max_y: maxY,
        min_y: minY,
        transition_on_update: false,
        markers: markers,
        brush: 'xy'
    });
}


String.prototype.trunc = String.prototype.trunc ||
    function (n) {
        return (this.length > n) ? this.substr(0, n - 1) + '...' : this;
    };