import React, { useEffect, useState } from "react";
import "./App.css";
import ReactEcharts from "echarts-for-react";

export default function App2() {
  const nNodes = 200;
  const nEdges = 1;
  const cluster = 0.05;
  const newGraph = true;

  const legend = ["1", "2", "3", "4", "5"];

  const graphOptions = {
    legend: {
      data: []
    },
    series: [
      {
        type: "graph",
        layout: "force",
        animation: false,
        label: {
          position: "right",
          formatter: "{b}"
        },
        draggable: true,
        roam: true,
        data: [],
        categories: [],
        force: {
          edgeLength: 30,
          repulsion: 20,
          gravity: 0.2
        },
        focusNodeAdjacency: true,
        edges: []
      }
    ]
  };

  const [options, setOptions] = useState(graphOptions);
  const colorsNew = [
    "#19c7b9",
    "#c71969",
    "#c78419",
    "#4f19c7",
    "#19c719",
    "#1984c7"
  ];
  const colorsOld = [
    "#c23531",
    "#2f4554",
    "#61a0a8",
    "#d48265",
    "#91c7ae",
    "#749f83",
    "#ca8622",
    "#bda29a",
    "#6e7074",
    "#546570",
    "#c4ccd3"
  ];
  useEffect(() => {
    let optionsCopy = JSON.parse(JSON.stringify(options));
    let colors;
    if (newGraph) {
      colors = colorsNew;
    } else {
      colors = colorsOld;
    }
    optionsCopy.legend.data = legend;
    optionsCopy.series[0].categories = legend.map(function (a, idx) {
      return {
        name: a,
        itemStyle: {
          normal: {
            color: colors[idx % colors.length]
          }
        }
      };
    });

    if (newGraph) {
      optionsCopy.series[0].lineStyle = {
        width: 0.5,
        curveness: 0.2,
        opacity: 0.7
      };
    }

    let nodes = [];
    let nodesByCategory = {};
    let nHighlight1 = 0;
    let nHighlight2 = 0;
    for (let i = 0; i < nNodes; i++) {
      const category = Math.floor(Math.random() * 5);
      let size = 10;
      if (i % (nNodes * 0.05) === 0) {
        size = Math.floor(Math.random() * 40);
      } else {
        size = Math.floor(Math.random() * 8);
      }
      if (size === 0) {
        size = 1;
      }

      let highlight1 = false;
      let highlight2 = false;
      if (!newGraph) {
        if (size > 30 && nHighlight1 < 5) {
          highlight1 = true;
          nHighlight1 = nHighlight1 + 1;
        } else if (size < 1 && nHighlight2 < 5) {
          highlight2 = true;
          nHighlight2 = nHighlight2 + 1;
        }
        size = 10;
      }
      let node = {
        name: i.toString(10),
        value: i,
        category: category,
        symbolSize: size
      };
      if (highlight1) {
        node.itemStyle = {
          normal: {
            borderColor: "#00ff00",
            borderWidth: 3
          }
        };
      } else if (highlight2) {
        node.itemStyle = {
          normal: {
            borderColor: "#ff00ff",
            borderWidth: 3
          }
        };
      }

      nodes.push(node);
      if (!nodesByCategory[category]) {
        nodesByCategory[category] = [];
      }
      nodesByCategory[category].push(node.value);
    }
    optionsCopy.series[0].data = nodes;

    let edges = [];
    nodes.forEach((node, idx) => {
      let dups = [idx];
      for (let i = 0; i < nEdges; i++) {
        let target = clusterSelect(nodesByCategory, node);
        while (dups.includes(target)) {
          target = clusterSelect(nodesByCategory, node);
        }
        dups.push(target);
        let edge = {
          source: idx,
          target: target
        };
        edges.push(edge);
      }
    });
    optionsCopy.series[0].edges = edges;

    analyze(nodes, edges);
    // console.log(optionsCopy);
    setOptions(optionsCopy);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function clusterSelect(nodesByCategory, node) {
    const r = Math.random();
    let target;
    if (r < cluster) {
      target =
        nodesByCategory[node.category][
          Math.floor(Math.random() * nodesByCategory[node.category].length)
        ];
    } else {
      target = Math.floor(Math.random() * nNodes);
    }
    return target;
  }

  function analyze(nodes, edges) {
    let buckets = [];
    nodes.forEach((node, idx) => {
      let m = edges.filter((e) => e.source === idx).length;
      let n = edges.filter((e) => e.target === idx).length;
      buckets.push(n + m);
    });
    const n = buckets.length;
    const mean = buckets.reduce((a, b) => a + b) / n;
    const s = Math.sqrt(
      buckets.map((x) => Math.pow(x - mean, 2)).reduce((a, b) => a + b) / n
    );
    console.log(
      "n",
      n,
      "mean",
      mean,
      "stdev",
      Number(s.toFixed(2)),
      "min",
      Math.min(...buckets),
      "max",
      Math.max(...buckets)
    );
  }

  return (
    <div className="App">
      <ReactEcharts
        style={{ height: "600px", width: "100%" }}
        option={options}
      />
    </div>
  );
}
