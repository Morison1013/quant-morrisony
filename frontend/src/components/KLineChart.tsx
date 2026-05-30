"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import type { KLineItem } from "@/lib/api";

interface Props {
  data: KLineItem[];
  loading?: boolean;
}

const MA_COLORS = ["#f59e0b", "#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f43f5e"];
const MA_LABELS = ["MA5", "MA10", "MA20", "MA30", "MA55", "MA60"];

export default function KLineChart({ data, loading }: Props) {
  const option = useMemo<EChartsOption>(() => {
    if (!data.length) return {};

    const dates = data.map((d) => d.date);
    const klineData = data.map((d) => [d.open, d.close, d.low, d.high]);
    const volumes = data.map((d) => d.volume);

    // MA 系列
    const maSeries = [
      data.map((d) => d.ma5 ?? null),
      data.map((d) => d.ma10 ?? null),
      data.map((d) => d.ma20 ?? null),
      data.map((d) => d.ma30 ?? null),
      data.map((d) => d.ma55 ?? null),
      data.map((d) => d.ma60 ?? null),
    ];

    // 成交量颜色（涨红跌绿）
    const volColors = data.map((d, i) => {
      if (i === 0) return d.close >= d.open ? "#ef4444" : "#22c55e";
      return d.close >= data[i - 1].close ? "#ef4444" : "#22c55e";
    });

    const opt: EChartsOption = {
      backgroundColor: "#0f172a",
      animation: false,
      legend: {
        data: ["K线", ...MA_LABELS, "BOLL", "成交量"],
        textStyle: { color: "#94a3b8", fontSize: 11 },
        top: 4,
        left: 60,
      },
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "cross",
          lineStyle: { color: "#475569" },
        },
        backgroundColor: "rgba(15,23,42,0.95)",
        borderColor: "#334155",
        textStyle: { color: "#e2e8f0" },
        formatter: (params: any) => {
          if (!params?.length) return "";
          const idx = params[0].dataIndex;
          const d = data[idx];
          let html = `<b>${d.date}</b><br/>`;
          html += `开: ${d.open} | 收: ${d.close}<br/>`;
          html += `高: ${d.high} | 低: ${d.low}<br/>`;
          html += `量: ${d.volume.toLocaleString()}<br/>`;
          MA_LABELS.forEach((label, i) => {
            const val = (d as any)[`ma${[5, 10, 20, 30, 55, 60][i]}`];
            if (val) html += `<span style="color:${MA_COLORS[i]}">${label}: ${val}</span><br/>`;
          });
          if (d.boll_upper) html += `<span style="color:#a78bfa">BOLL上: ${d.boll_upper}</span><br/>`;
          if (d.boll_mid) html += `<span style="color:#fbbf24">BOLL中: ${d.boll_mid}</span><br/>`;
          if (d.boll_lower) html += `<span style="color:#a78bfa">BOLL下: ${d.boll_lower}</span><br/>`;
          return html;
        },
      },
      grid: [
        { left: 60, right: 30, top: 40, height: "55%" },
        { left: 60, right: 30, top: "68%", height: "22%" },
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
        // K 线
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
        // MA 线
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
        // BOLL 通道
        {
          name: "BOLL",
          type: "line" as const,
          data: data.map((d) => d.boll_mid ?? null),
          smooth: true,
          symbol: "none",
          lineStyle: { width: 1, color: "#fbbf24", type: "solid" },
          xAxisIndex: 0,
          yAxisIndex: 0,
        },
        {
          name: "BOLL上",
          type: "line" as const,
          data: data.map((d) => d.boll_upper ?? null),
          smooth: true,
          symbol: "none",
          lineStyle: { width: 1, color: "#a78bfa", type: "dashed" },
          xAxisIndex: 0,
          yAxisIndex: 0,
        },
        {
          name: "BOLL下",
          type: "line" as const,
          data: data.map((d) => d.boll_lower ?? null),
          smooth: true,
          symbol: "none",
          lineStyle: { width: 1, color: "#a78bfa", type: "dashed" },
          xAxisIndex: 0,
          yAxisIndex: 0,
        },
        // 成交量柱状图
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
  }, [data]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-slate-900 rounded-xl border border-slate-700">
        <span className="text-slate-400 animate-pulse">加载中...</span>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700 p-2">
      <div className="flex items-center gap-4 mb-2 px-2">
        <h2 className="text-sm font-semibold text-slate-200">K 线图 · 前复权</h2>
        <div className="flex gap-3 text-xs">
          {MA_LABELS.map((label, i) => (
            <span key={label} style={{ color: MA_COLORS[i] }}>
              {label}
            </span>
          ))}
        </div>
      </div>
      <ReactECharts option={option} style={{ height: "520px", width: "100%" }} />
    </div>
  );
}
