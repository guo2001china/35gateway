// src/components/AudioPlayer.js
import React, { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';

const WaveformPlayer = ({audioUrl, onDurationChange}: {audioUrl: string, onDurationChange?: (duration: number) => void}) => {

  const waveformRef = useRef(null);
  const waveSurferRef = useRef<WaveSurfer | null>(null);

useEffect(() => {
    let waveSurfer: WaveSurfer | null = null;
    if (waveformRef.current) {
      const rootStyles = getComputedStyle(document.documentElement);
      const accent = rootStyles.getPropertyValue('--film-accent').trim() || '#1d7bff';
      const accentStrong = rootStyles.getPropertyValue('--film-accent-strong').trim() || '#0c61db';
      const lineStrong = rootStyles.getPropertyValue('--film-line-strong').trim() || 'rgba(17, 38, 66, 0.12)';
      waveSurfer = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: lineStrong,
        progressColor: accent,
        cursorColor: accentStrong,
        url: audioUrl,
        fillParent: true,
        height: 64,
        barWidth: 3,
        barGap: 2,
        barRadius: 4,
      });
      // 获取音频时长
      waveSurfer.on('ready', () => {
        const duration = waveSurfer!.getDuration();
        onDurationChange?.(duration);
      });
      waveSurferRef.current = waveSurfer;

    }
    return () => {
      if (waveSurfer) {
        waveSurfer.destroy();
      }
    }
  }, [audioUrl, onDurationChange])

  const handlePlayPause = () => {
    if (waveSurferRef.current) {
      waveSurferRef.current.playPause();
    }
  };

  return (
    <div className="waveform-player" onClick={handlePlayPause} style={{width: '100%'}} ref={waveformRef}></div>
  )
}

export default WaveformPlayer;
