// ──────────────────────────────────────────────
// 刷新频率控制 + 设置面板
// ──────────────────────────────────────────────

"use client";

import React, { useState } from "react";
import { useEmotion } from "@/lib/emotionStore";
import type { AlertConfig } from "@/lib/emotionTypes";

/* ── 复盘时间指示器 ── */
export function ReviewTimeIndicator() {
  const { lastFetch, nextFetch, refresh } = useEmotion();

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-slate-500">上次拉取</span>
        <span className="text-[10px] text-slate-300 font-mono">{lastFetch || "—"}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-slate-500">下次复盘</span>
        <span className="text-[10px] text-emerald-400 font-mono">{nextFetch || "—"}</span>
      </div>

      {/* 手动刷新 */}
      <button
        onClick={refresh}
        className="px-2 py-1 text-xs rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-400 hover:bg-blue-600/30 transition-colors font-medium"
      >
        ↻ 手动复盘
      </button>
    </div>
  );
}

/* ── 设置面板 ── */
export function SettingsPanel() {
  const { alerts, setAlerts } = useEmotion();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="p-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors"
        title="设置"
      >
        ⚙
      </button>

      {open && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)}>
          <div
            className="bg-slate-900 rounded-xl border border-slate-700 p-6 w-96 max-h-[80vh] overflow-y-auto shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-slate-100">⚙️ 预警设置</h2>
              <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-200 text-lg">
                ✕
              </button>
            </div>

            <div className="space-y-4">
              {/* 声音预警 */}
              <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-sm text-slate-200">声音预警</span>
                  <input
                    type="checkbox"
                    checked={alerts.soundEnabled}
                    onChange={(e) => setAlerts({ ...alerts, soundEnabled: e.target.checked })}
                    className="h-4 w-4 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-0"
                  />
                </label>
                <p className="text-[10px] text-slate-500 mt-1">预警时播放提示音</p>
              </div>

              {/* 桌面通知 */}
              <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-sm text-slate-200">桌面通知</span>
                  <input
                    type="checkbox"
                    checked={alerts.desktopNotify}
                    onChange={(e) => setAlerts({ ...alerts, desktopNotify: e.target.checked })}
                    className="h-4 w-4 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-0"
                  />
                </label>
                <p className="text-[10px] text-slate-500 mt-1">触发预警时弹出浏览器通知</p>
              </div>

              {/* 自定义音频 */}
              <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                <label className="text-sm text-slate-200 block mb-2">自定义预警音频</label>
                <input
                  type="file"
                  accept="audio/*"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      const url = URL.createObjectURL(file);
                      setAlerts({ ...alerts, customSoundUrl: url });
                    }
                  }}
                  className="text-xs text-slate-400 file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:bg-slate-700 file:text-slate-200 file:text-xs file:cursor-pointer"
                />
                {alerts.customSoundUrl && (
                  <div className="mt-2 flex items-center gap-2">
                    <audio controls src={alerts.customSoundUrl} className="h-6 w-full" />
                    <button
                      onClick={() => setAlerts({ ...alerts, customSoundUrl: null })}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      移除
                    </button>
                  </div>
                )}
              </div>

              {/* 测试按钮 */}
              <button
                onClick={() => {
                  if (alerts.soundEnabled) {
                    if (alerts.customSoundUrl) {
                      new Audio(alerts.customSoundUrl).play().catch(() => {});
                    } else {
                      const ctx = new AudioContext();
                      const osc = ctx.createOscillator();
                      const gain = ctx.createGain();
                      osc.connect(gain);
                      gain.connect(ctx.destination);
                      osc.frequency.value = 800;
                      gain.gain.value = 0.3;
                      osc.start();
                      setTimeout(() => { osc.stop(); ctx.close(); }, 200);
                    }
                  }
                  if (alerts.desktopNotify && "Notification" in window) {
                    Notification.requestPermission().then((perm) => {
                      if (perm === "granted") {
                        new Notification("预警测试", { body: "声音和桌面通知正常！" });
                      }
                    });
                  }
                }}
                className="w-full py-2 text-sm rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-400 hover:bg-blue-600/30 transition-colors font-medium"
              >
                🔔 测试预警
              </button>

              {/* 数据说明 */}
              <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/30">
                <p className="text-[10px] text-slate-500">
                  📊 数据来源：通达信 SQLite 日线数据
                  <br />
                  🕐 自动拉取：每日 12:00（午间复盘）和 14:30（尾盘复盘）
                  <br />
                  ⚡ 可点击「手动复盘」按钮立即刷新
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
