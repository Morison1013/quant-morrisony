"use client";

import React, { useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import type { KLineItem } from "@/lib/api";

interface Props {
  data: KLineItem[];
  loading?: boolean;
}

// 同花顺风格颜色配置
const COLORS = {
  // K线颜色（红涨绿跌）
  rise: "#ff4d4f",      // 涨 - 红色
  fall: "#26a69a",      // 跌 - 绿色

  // 均线颜色
  ma5: "#f59e0b",       // MA5 - 黄色
  ma10: "#3b82f6",      // MA10 - 蓝色
  ma20: "#a78bfa",      // MA20 - 紫色
  ma30: "#06b6d4",      // MA30 - 青色
  ma60: "#f43f5e",      // MA60 - 红粉色

  // BOLL颜色
  boll: "#fbbf24",      // BOLL中轨 - 金色
  bollBand: "#a78bfa",  // BOLL上下轨 - 紫色

  // MACD颜色
  macdDif: "#f59e0b",   // DIF - 黄色
  macdDea: "#3b82f6",   // DEA - 蓝色
  macdBarRise: "#ff4d4f", // MACD柱涨 - 红色
  macdBarFall: "#26a69a", // MACD柱跌 - 绿色

  // 背景/边框
  background: "#1a1a2e",
  gridLine: "#2d2d44",
  axisLine: "#3d3d5c",
  textColor: "#9ca3af",
  crossLine: "#f59e0b",
};

const MA_LABELS = ["MA5", "MA10", "MA20", "MA30", "MA60"];
const MA_COLORS = [COLORS.ma5, COLORS.ma10, COLORS.ma20, COLORS.ma30, COLORS.ma60];

type Period = "daily" | "weekly" | "monthly";

export default function KLineChart({ data, loading }: Props) {
  const [period, setPeriod] = useState<Period>("daily");
  const [showMACD, setShowMACD] = useState(true);
  const [showBOLL, setShowBOLL] = useState(false);
  const [showVolume, setShowVolume] = useState(true);

  // 根据周期聚合数据
  const aggregatedData = useMemo(() => {
    if (!data.length) return [];

    if (period === "daily") return data;

    // 周线/月线聚合
    const result: KLineItem[] = [];
    let group: KLineItem[] = [];

    const getPeriodKey = (date: string, p: Period) => {
      const d = new Date(date);
      if (p === "weekly") {
        // 按周分组（周一为起始）
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1);
        return new Date(d.setDate(diff)).toISOString().slice(0, 10);
      } else if (p === "monthly") {
        return date.slice(0, 7); // YYYY-MM
      }
      return date;
    };

    let currentKey = "";

    for (const item of data) {
      const key = getPeriodKey(item.date, period);
      if (key !== currentKey && group.length > 0) {
        // 聚合上一组
        const first = group[0];
        const last = group[group.length - 1];
        result.push({
          date: currentKey,
          open: first.open,
          close: last.close,
          high: Math.max(...group.map(g => g.high)),
          low: Math.min(...group.map(g => g.low)),
          volume: group.reduce((sum, g) => sum + g.volume, 0),
          ma5: last.ma5,
          ma10: last.ma10,
          ma20: last.ma20,
          ma30: last.ma30,
          ma60: last.ma60,
          boll_upper: last.boll_upper,
          boll_mid: last.boll_mid,
          boll_lower: last.boll_lower,
        });
        group = [];
      }
      currentKey = key;
      group.push(item);
    }

    // 最后一组
    if (group.length > 0) {
      const first = group[0];
      const last = group[group.length - 1];
      result.push({
        date: currentKey,
        open: first.open,
        close: last.close,
        high: Math.max(...group.map(g => g.high)),
        low: Math.min(...group.map(g => g.low)),
        volume: group.reduce((sum, g) => sum + g.volume, 0),
        ma5: last.ma5,
        ma10: last.ma10,
        ma20: last.ma20,
        ma30: last.ma30,
        ma60: last.ma60,
        boll_upper: last.boll_upper,
        boll_mid: last.boll_mid,
        boll_lower: last.boll_lower,
      });
    }

    return result;
  }, [data, period]);

  // 计算MACD
  const macdData = useMemo(() => {
    if (!aggregatedData.length) return { dif: [], dea: [], bar: [] };

    // 计算EMA
    const calcEMA = (data: number[], period: number) => {
      const result: number[] = [];
      const k = 2 / (period + 1);
      let ema = data[0];
      for (let i = 0; i < data.length; i++) {
        if (i === 0) {
          result.push(data[0]);
          ema = data[0];
        } else {
          ema = k * data[i] + (1 - k) * ema;
          result.push(ema);
        }
      }
      return result;
    };

    const closes = aggregatedData.map(d => d.close);
    const dif = calcEMA(closes, 12).map((v, i) => v - calcEMA(closes, 26)[i]);
    const dea = calcEMA(dif, 9);
    const bar = dif.map((v, i) => 2 * (v - dea[i]));

    return { dif, dea, bar };
  }, [aggregatedData]);

  const option = useMemo<EChartsOption>(() => {
    if (!aggregatedData.length) return {};

    const dates = aggregatedData.map((d) => d.date);
    const klineData = aggregatedData.map((d) => [d.open, d.close, d.low, d.high]);
    const volumes = aggregatedData.map((d) => d.volume);

    // 均线数据
    const maSeries = [
      aggregatedData.map((d) => d.ma5 ?? null),
      aggregatedData.map((d) => d.ma10 ?? null),
      aggregatedData.map((d) => d.ma20 ?? null),
      aggregatedData.map((d) => d.ma30 ?? null),
      aggregatedData.map((d) => d.ma60 ?? null),
    ];

    // 成交量颜色
    const volColors = aggregatedData.map((d, i) => {
      if (i === 0) return d.close >= d.open ? COLORS.rise : COLORS.fall;
      return d.close >= aggregatedData[i - 1].close ? COLORS.rise : COLORS.fall;
    });

    // MACD柱颜色
    const macdBarColors = macdData.bar.map((v) =>
      v >= 0 ? COLORS.macdBarRise : COLORS.macdBarFall
    );

    // 最新价格
    const lastData = aggregatedData[aggregatedData.length - 1];
    const lastPrice = lastData.close;

    // 计算Y轴范围
    const prices = aggregatedData.flatMap((d) => [d.high, d.low]);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice;
    const yMin = Math.floor(minPrice - priceRange * 0.1);
    const yMax = Math.ceil(maxPrice + priceRange * 0.1);

    const gridConfig = showMACD
      ? [
        { left: 70, right: 60, top: 35, height: "50%" },  // K线
        { left: 70, right: 60, top: "60%", height: "18%" }, // 成交量
        { left: 70, right: 60, top: "82%", height: "12%" }, // MACD
      ]
      : [
        { left: 70, right: 60, top: 35, height: "60%" },  // K线
        { left: 70, right: 60, top: "68%", height: "24%" }, // 成交量
      ];

    const series: any[] = [
      // K线
      {
        name: "K线",
        type: "candlestick",
        data: klineData,
        itemStyle: {
          color: COLORS.rise,
          color0: COLORS.fall,
          borderColor: COLORS.rise,
          borderColor0: COLORS.fall,
        },
        xAxisIndex: 0,
        yAxisIndex: 0,
        markPoint: {
          symbol: 'pin',
          symbolSize: 40,
          data: [
            {
              name: '最新',
              value: lastPrice.toFixed(2),
              coord: [dates.length - 1, lastPrice],
              itemStyle: { color: lastData.close >= lastData.open ? COLORS.rise : COLORS.fall },
              label: {
                color: '#fff',
                fontSize: 11,
                formatter: (p: any) => p.value,
              },
            },
          ],
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: COLORS.crossLine, width: 1, type: 'dashed' },
          data: [
            { yAxis: lastPrice, label: { formatter: lastPrice.toFixed(2), position: 'end' } },
          ],
        },
      },
      // 均线
      ...maSeries.map((seriesData, i) => ({
        name: MA_LABELS[i],
        type: "line" as const,
        data: seriesData,
        smooth: false,
        symbol: "none",
        lineStyle: { width: 1.5, color: MA_COLORS[i] },
        xAxisIndex: 0,
        yAxisIndex: 0,
      })),
    ];

    // BOLL通道
    if (showBOLL) {
      series.push(
        {
          name: "BOLL中",
          type: "line",
          data: aggregatedData.map((d) => d.boll_mid ?? null),
          smooth: false,
          symbol: "none",
          lineStyle: { width: 1.5, color: COLORS.boll },
          xAxisIndex: 0,
          yAxisIndex: 0,
        },
        {
          name: "BOLL上",
          type: "line",
          data: aggregatedData.map((d) => d.boll_upper ?? null),
          smooth: false,
          symbol: "none",
          lineStyle: { width: 1, color: COLORS.bollBand, type: "solid" },
          areaStyle: { color: 'transparent' },
          xAxisIndex: 0,
          yAxisIndex: 0,
        },
        {
          name: "BOLL下",
          type: "line",
          data: aggregatedData.map((d) => d.boll_lower ?? null),
          smooth: false,
          symbol: "none",
          lineStyle: { width: 1, color: COLORS.bollBand, type: "solid" },
          xAxisIndex: 0,
          yAxisIndex: 0,
        },
      );
    }

    // 成交量
    if (showVolume) {
      series.push({
        name: "成交量",
        type: "bar",
        data: volumes.map((v, i) => ({
          value: v,
          itemStyle: { color: volColors[i] },
        })),
        xAxisIndex: 1,
        yAxisIndex: 1,
        barWidth: '60%',
      });
    }

    // MACD
    if (showMACD) {
      series.push(
        {
          name: "MACD-DIF",
          type: "line",
          data: macdData.dif,
          smooth: false,
          symbol: "none",
          lineStyle: { width: 1.5, color: COLORS.macdDif },
          xAxisIndex: showVolume ? 2 : 1,
          yAxisIndex: showVolume ? 2 : 1,
        },
        {
          name: "MACD-DEA",
          type: "line",
          data: macdData.dea,
          smooth: false,
          symbol: "none",
          lineStyle: { width: 1.5, color: COLORS.macdDea },
          xAxisIndex: showVolume ? 2 : 1,
          yAxisIndex: showVolume ? 2 : 1,
        },
        {
          name: "MACD柱",
          type: "bar",
          data: macdData.bar.map((v, i) => ({
            value: v,
            itemStyle: { color: macdBarColors[i] },
          })),
          xAxisIndex: showVolume ? 2 : 1,
          yAxisIndex: showVolume ? 2 : 1,
          barWidth: '40%',
        },
      );
    }

    const opt: EChartsOption = {
      backgroundColor: COLORS.background,
      animation: false,
      legend: {
        show: false,
      },
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "cross",
          lineStyle: { color: COLORS.crossLine, width: 1 },
          crossStyle: { color: COLORS.crossLine, width: 1 },
        },
        backgroundColor: "rgba(26,26,46,0.95)",
        borderColor: COLORS.axisLine,
        borderWidth: 1,
        textStyle: { color: "#e2e8f0", fontSize: 12 },
        formatter: (params: any) => {
          if (!params?.length) return "";
          const idx = params[0].dataIndex;
          const d = aggregatedData[idx];
          const chg = idx > 0 ? ((d.close - aggregatedData[idx-1].close) / aggregatedData[idx-1].close * 100).toFixed(2) : "0.00";
          const chgColor = parseFloat(chg) >= 0 ? COLORS.rise : COLORS.fall;
          const chgSign = parseFloat(chg) >= 0 ? "+" : "";

          let html = `<div style="padding:4px 8px;font-size:12px;line-height:1.6">`;
          html += `<div style="font-weight:bold;color:#fff">${d.date}</div>`;
          html += `<div style="margin-top:4px">`;
          html += `<span style="color:${COLORS.textColor}">开:</span> <span style="color:#fff">${d.open.toFixed(2)}</span> `;
          html += `<span style="color:${COLORS.textColor}">高:</span> <span style="color:${COLORS.rise}">${d.high.toFixed(2)}</span> `;
          html += `<span style="color:${COLORS.textColor}">低:</span> <span style="color:${COLORS.fall}">${d.low.toFixed(2)}</span>`;
          html += `</div>`;
          html += `<div>`;
          html += `<span style="color:${COLORS.textColor}">收:</span> <span style="color:${d.close >= d.open ? COLORS.rise : COLORS.fall}">${d.close.toFixed(2)}</span> `;
          html += `<span style="color:${chgColor}">${chgSign}${chg}%</span>`;
          html += `</div>`;
          html += `<div><span style="color:${COLORS.textColor}">量:</span> <span style="color:#fff">${(d.volume/10000).toFixed(0)}万</span></div>`;
          html += `<div style="margin-top:4px;border-top:1px solid ${COLORS.gridLine};padding-top:4px">`;
          MA_LABELS.forEach((label, i) => {
            const val = maSeries[i][idx];
            if (val) html += `<span style="color:${MA_COLORS[i]}">${label}:${val.toFixed(2)}</span> `;
          });
          html += `</div>`;
          html += `</div>`;
          return html;
        },
      },
      grid: gridConfig,
      axisPointer: {
        link: [{ xAxisIndex: 'all' }],
      },
      xAxis: gridConfig.map((_, i) => ({
        type: "category",
        data: dates,
        gridIndex: i,
        axisLine: { lineStyle: { color: COLORS.axisLine, width: 1 } },
        axisTick: { show: i === gridConfig.length - 1, lineStyle: { color: COLORS.axisLine } },
        axisLabel: {
          show: i === gridConfig.length - 1,
          color: COLORS.textColor,
          fontSize: 10,
          formatter: (v: string) => period === "monthly" ? v.slice(0,7) : v.slice(5),
          margin: 4,
        },
        splitLine: { show: false },
      })),
      yAxis: [
        // K线Y轴
        {
          scale: true,
          gridIndex: 0,
          min: yMin,
          max: yMax,
          axisLine: { show: true, lineStyle: { color: COLORS.axisLine, width: 1 } },
          axisTick: { show: true, lineStyle: { color: COLORS.axisLine } },
          axisLabel: {
            color: COLORS.textColor,
            fontSize: 10,
            formatter: (v: number) => v.toFixed(2),
            margin: 4,
          },
          splitLine: {
            show: true,
            lineStyle: { color: COLORS.gridLine, width: 0.5 },
          },
          splitArea: { show: false },
        },
        // 成交量Y轴
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { show: false },
          splitLine: { show: false },
        },
        // MACD Y轴（如果显示）
        ...(showMACD ? [{
          scale: true,
          gridIndex: 2,
          splitNumber: 2,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            show: true,
            color: COLORS.textColor,
            fontSize: 9,
            formatter: (v: number) => v.toFixed(2),
            margin: 2,
          },
          splitLine: { show: false },
        }] : []),
      ],
      series,
      dataZoom: [
        {
          type: "inside",
          xAxisIndex: gridConfig.map((_, i) => i),
          start: 70,
          end: 100,
          minValueSpan: 20,
        },
        {
          type: "slider",
          xAxisIndex: gridConfig.map((_, i) => i),
          start: 70,
          end: 100,
          bottom: 8,
          height: 20,
          borderColor: "transparent",
          backgroundColor: COLORS.gridLine,
          fillerColor: "rgba(245,158,11,0.2)",
          handleStyle: { color: COLORS.ma5, borderColor: COLORS.ma5 },
          textStyle: { color: COLORS.textColor, fontSize: 10 },
          dataBackground: {
            lineStyle: { color: COLORS.ma5 },
            areaStyle: { color: "rgba(245,158,11,0.1)" },
          },
        },
      ],
    };

    return opt;
  }, [aggregatedData, macdData, showMACD, showBOLL, showVolume, period]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[600px] bg-[#1a1a2e] rounded-lg border border-[#2d2d44]">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-[#f59e0b] border-t-transparent rounded-full mx-auto mb-3"></div>
          <span className="text-[#9ca3af] text-sm">加载中...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#1a1a2e] rounded-lg border border-[#2d2d44] overflow-hidden">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#2d2d44]">
        {/* 周期切换 */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#9ca3af] mr-2">周期:</span>
          {(["daily", "weekly", "monthly"] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2.5 py-1 text-xs rounded ${
                period === p
                  ? "bg-[#f59e0b] text-white"
                  : "bg-[#2d2d44] text-[#9ca3af] hover:bg-[#3d3d5c]"
              }`}
            >
              {p === "daily" ? "日线" : p === "weekly" ? "周线" : "月线"}
            </button>
          ))}
        </div>

        {/* 均线显示 */}
        <div className="flex items-center gap-3">
          {MA_LABELS.map((label, i) => (
            <span key={label} className="text-xs" style={{ color: MA_COLORS[i] }}>
              {label}
            </span>
          ))}
        </div>

        {/* 指标切换 */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowVolume(!showVolume)}
            className={`px-2 py-1 text-xs rounded ${
              showVolume ? "bg-[#2d2d44] text-[#f59e0b]" : "bg-[#2d2d44] text-[#9ca3af]"
            }`}
          >
            VOL
          </button>
          <button
            onClick={() => setShowMACD(!showMACD)}
            className={`px-2 py-1 text-xs rounded ${
              showMACD ? "bg-[#2d2d44] text-[#f59e0b]" : "bg-[#2d2d44] text-[#9ca3af]"
            }`}
          >
            MACD
          </button>
          <button
            onClick={() => setShowBOLL(!showBOLL)}
            className={`px-2 py-1 text-xs rounded ${
              showBOLL ? "bg-[#2d2d44] text-[#f59e0b]" : "bg-[#2d2d44] text-[#9ca3af]"
            }`}
          >
            BOLL
          </button>
        </div>
      </div>

      {/* 图表 */}
      <ReactECharts
        option={option}
        style={{ height: showMACD ? "550px" : "480px", width: "100%" }}
        opts={{ renderer: 'canvas' }}
      />

      {/* 底部信息 */}
      {aggregatedData.length > 0 && (
        <div className="flex items-center justify-between px-3 py-1.5 border-t border-[#2d2d44] text-xs">
          <span className="text-[#9ca3af]">
            数据范围: {aggregatedData[0].date} ~ {aggregatedData[aggregatedData.length-1].date}
          </span>
          <span className="text-[#9ca3af]">
            共 {aggregatedData.length} 根K线
          </span>
        </div>
      )}
    </div>
  );
}