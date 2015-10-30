function getRandomValues() {
    // data setup
    var values = new Array(20);

    for (var i = 0; i < values.length; i++){
        values[i] = [5 + randomVal(), 10 + randomVal(), 15 + randomVal(), 20 + randomVal(), 30 + randomVal(),
            35 + randomVal(), 40 + randomVal(), 45 + randomVal(), 50 + randomVal()]
    }

    return values;
}

function randomVal(){
    return Math.floor( Math.random() * 80 );
}


if( $('.number-chart .inlinesparkline').length > 0 ) {

    var randomVal = getRandomValues();
    var sparklineNumberChart = function() {

        var params = {
            width: '140px',
            height: '30px',
            lineWidth: '2',
            lineColor: '#1D92AF',
            fillColor: false,
            spotRadius: '2',
            highlightLineColor: '#aedaff',
            highlightSpotColor: '#71aadb',
            spotColor: false,
            minSpotColor: false,
            maxSpotColor: false,
            disableInteraction: false
        };

        $('#number-chart1').sparkline(randomVal[0], params);
        $('#number-chart2').sparkline(randomVal[1], params);
        $('#number-chart3').sparkline(randomVal[2], params);
        $('#number-chart4').sparkline(randomVal[3], params);
    };

    sparklineNumberChart();
}

/* sparkline on window resize */
var sparkResize;

$(window).resize(function(e) {
    clearTimeout(sparkResize);

    if( $('.sparkline-stat-item .inlinesparkline').length > 0 ) {
        sparkResize = setTimeout(sparklineStat, 200);
    }

    if( $('.secondary-stat-item .inlinesparkline').length > 0 ) {
        sparkResize = setTimeout(sparklineWidget, 200);
    }
});