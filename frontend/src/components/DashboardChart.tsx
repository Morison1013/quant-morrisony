"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import type { DashboardKLineItem } from "@/lib/api";

interface Props {
  data: DashboardKLineItem[];
  name: string;
  frequency?: string;
  loading?: boolean;
}

const MA_COLORS = ["#f59e0b", "#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f43f5e"];
const MA_LABELS = ["MA5", "MA10", "MA20", "MA30", "MA55", "MA60"];

function buildLineOption(data: DashboardKLineItem[], name: string): EChartsOption {
  if (!data.length) return { backgroundColor: "#0f172a" };

  const times = data.map((d) => d.date);
  const closes = data.map((d) => d.close);

  const opt: EChartsOption = {
    backgroundColor: "#0f172a",
    animation: false,
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross", lineStyle: { color: "#475569" } },
      backgroundColor: "rgba(15,23,42,0.95)",
      borderColor: "#334155",
      textStyle: { color: "#e2e8f0" },
      formatter: (params: any) => {
        if (!params?.length) return "";
        const idx = params[0].dataIndex;
        const d = data[idx];
        let html = `<b>${name} · ${d.date}</b><br/>`;
        html += `价格: ${d.close}<br/>`;
        if (d.amount) html += `额: ${(d.amount / 1e8).toFixed(2)} 亿<br/>`;
        MA_LABELS.forEach((label, i) => {
          const val = (d as any)[`ma${[5, 10, 20, 30, 55, 60][i]}`];
          if (val) html += `<span style="color:${MA_COLORS[i]}">${label}: ${val}</span><br/>`;
        });
        return html;
      },
    },
    grid: [
      { left: 70, right: 30, top: 30, height: "60%" },
      { left: 70, right: 30, top: "72%", height: "18%" },
    ],
    xAxis: [
      {
        type: "category",
        data: times,
        gridIndex: 0,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
      {
        type: "category",
        data: times,
        gridIndex: 1,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8", fontSize: 9, formatter: (v: string) => v.slice(11) || v.slice(5) },
        splitLine: { show: false },
      },
    ],
    yAxis: [
      {
        scale: true,
        gridIndex: 0,
        splitArea: { show: true, areaStyle: { color: ["#0f172a", "#1e293b"] } },
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
    ],
    series: [
      // 分时折线
      {
        name: name,
        type: "line",
        data: closes,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1.5, color: "#3b82f6" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(59,130,246,0.3)" },
              { offset: 1, color: "rgba(59,130,246,0.02)" },
            ],
          },
        },
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      // MA 线
      ...MA_LABELS.map((label, i) => ({
        name: label,
        type: "line" as const,
        data: data.map((d) => (d as any)[`ma${[5, 10, 20, 30, 55, 60][i]}`] ?? null),
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1, color: MA_COLORS[i] },
        xAxisIndex: 0,
        yAxisIndex: 0,
      })),
      // 成交量
      {
        name: "成交量",
        type: "bar" as const,
        data: data.map((d) => d.volume),
        itemStyle: { color: "#334155" },
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ],
    dataZoom: [
      {
        type: "inside",
        xAxisIndex: [0, 1],
        start: 0,
        end: 100,
        minValueSpan: 10,
      },
    ],
  };

  return opt;
}

function buildCandleOption(data: DashboardKLineItem[], name: string): EChartsOption {
  if (!data.length) return { backgroundColor: "#0f172a" };

  const dates = data.map((d) => d.date);
  const klineData = data.map((d) => [d.open, d.close, d.low, d.high]);
  const volumes = data.map((d) => d.volume);

  const maSeries = [
    data.map((d) => d.ma5 ?? null),
    data.map((d) => d.ma10 ?? null),
    data.map((d) => d.ma20 ?? null),
    data.map((d) => d.ma30 ?? null),
    data.map((d) => d.ma55 ?? null),
    data.map((d) => d.ma60 ?? null),
  ];

  const volColors = data.map((d, i) => {
    if (i === 0) return d.close >= d.open ? "#ef4444" : "#22c55e";
    return d.close >= data[i - 1].close ? "#ef4444" : "#22c55e";
  });

  const opt: EChartsOption = {
    backgroundColor: "#0f172a",
    animation: false,
    legend: {
      data: ["K线", ...MA_LABELS, "成交量"],
      textStyle: { color: "#94a3b8", fontSize: 11 },
      top: 4,
      left: 60,
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross", lineStyle: { color: "#475569" } },
      backgroundColor: "rgba(15,23,42,0.95)",
      borderColor: "#334155",
      textStyle: { color: "#e2e8f0" },
      formatter: (params: any) => {
        if (!params?.length) return "";
        const idx = params[0].dataIndex;
        const d = data[idx];
        let html = `<b>${name} · ${d.date}</b><br/>`;
        html += `开: ${d.open} | 收: ${d.close}<br/>`;
        html += `高: ${d.high} | 低: ${d.low}<br/>`;
        html += `量: ${d.volume.toLocaleString()}<br/>`;
        if (d.amount) html += `额: ${(d.amount / 1e8).toFixed(2)} 亿<br/>`;
        MA_LABELS.forEach((label, i) => {
          const val = (d as any)[`ma${[5, 10, 20, 30, 55, 60][i]}`];
          if (val) html += `<span style="color:${MA_COLORS[i]}">${label}: ${val}</span><br/>`;
        });
        return html;
      },
    },
    grid: [
      { left: 70, right: 30, top: 40, height: "55%" },
      { left: 70, right: 30, top: "68%", height: "22%" },
    ],
    xAxis: [
      {
        type: "category",
        data: dates,
        gridIndex: 0,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
      {
        type: "category",
        data: dates,
        gridIndex: 1,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8", fontSize: 10, formatter: (v: string) => v.slice(5) },
        splitLine: { show: false },
      },
    ],
    yAxis: [
      {
        scale: true,
        gridIndex: 0,
        splitArea: { show: true, areaStyle: { color: ["#0f172a", "#1e293b"] } },
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "K线",
        type: "candlestick",
        data: klineData,
        itemStyle: {
          color: "#ef4444",
          color0: "#22c55e",
          borderColor: "#ef4444",
          borderColor0: "#22c55e",
        },
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      ...maSeries.map((seriesData, i) => ({
        name: MA_LABELS[i],
        type: "line" as const,
        data: seriesData,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1, color: MA_COLORS[i] },
        xAxisIndex: 0,
        yAxisIndex: 0,
      })),
      {
        name: "成交量",
        type: "bar" as const,
        data: volumes.map((v, i) => ({
          value: v,
          itemStyle: { color: volColors[i] },
        })),
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ],
    dataZoom: [
      {
        type: "inside",
        xAxisIndex: [0, 1],
        start: 50,
        end: 100,
        minValueSpan: 10,
      },
      {
        type: "slider",
        xAxisIndex: [0, 1],
        start: 50,
        end: 100,
        bottom: 10,
        height: 18,
        borderColor: "transparent",
        backgroundColor: "#1e293b",
        fillerColor: "#334155",
        handleStyle: { color: "#64748b" },
        textStyle: { color: "#94a3b8" },
      },
    ],
  };

  return opt;
}

export default function DashboardChart({ data, name, frequency = "daily", loading }: Props) {
  const isLine = frequency === "5min";

  const option = useMemo(() => {
    if (isLine) {
      return buildLineOption(data, name);
    }
    return buildCandleOption(data, name);
  }, [data, name, isLine]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-72 bg-slate-900">
        <span className="text-slate-400 animate-pulse text-xs">加载中...</span>
      </div>
    );
  }

  return (
    <ReactECharts option={option} style={{ height: isLine ? "380px" : "420px", width: "100%" }} />
  );
}
