// ──────────────────────────────────────────────
// 迷你分时图 — 用于表格内嵌预览
// ──────────────────────────────────────────────

"use client";

import React, { useRef, useEffect } from "react";

interface Props {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export default function MiniChart({ data, width = 100, height = 28, color = "#3b82f6" }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data.length) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    ctx.clearRect(0, 0, width, height);

    // 渐变填充
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    const lastVal = data[data.length - 1];
    const isUp = lastVal >= data[0];
    if (isUp) {
      gradient.addColorStop(0, "rgba(239,68,68,0.3)");
      gradient.addColorStop(1, "rgba(239,68,68,0)");
    } else {
      gradient.addColorStop(0, "rgba(34,197,94,0.3)");
      gradient.addColorStop(1, "rgba(34,197,94,0)");
    }

    ctx.beginPath();
    data.forEach((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    // 填充区域
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // 折线
    ctx.beginPath();
    data.forEach((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = isUp ? "#ef4444" : "#22c55e";
    ctx.lineWidth = 1;
    ctx.stroke();
  }, [data, width, height]);

  return <canvas ref={canvasRef} style={{ width, height, display: "block" }} />;
}
