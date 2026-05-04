<script lang="ts">
  import { onMount } from 'svelte';
  import type { FlowSection } from '../lib/types';

  export let sections: FlowSection[] = [];
  export let compact = false;

  let canvas: HTMLCanvasElement;

  const sectionEnergies: Record<string, number> = {
    centering: 0.2,
    'warm up': 0.4,
    warmup: 0.4,
    'sun salutations': 0.6,
    standing: 0.7,
    peak: 0.85,
    floor: 0.5,
    'cool down': 0.35,
    cooldown: 0.35,
    savasana: 0.1,
  };

  $: chartLabel = buildChartLabel(sections);

  function buildChartLabel(items: FlowSection[]): string {
    if (!items.length) return 'Energy curve chart (no sections)';
    const parts = items.map((s) => {
      const energy = sectionEnergies[s.label.toLowerCase()] ?? 0.5;
      return `${s.label} ${(energy * 100).toFixed(0)}%`;
    });
    return `Energy curve chart: ${parts.join(', ')}`;
  }

  $: if (canvas && sections.length > 0) {
    drawChart();
  }

  function drawChart() {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const padding = 30;

    ctx.clearRect(0, 0, width, height);

    // Build data points
    const points: { x: number; y: number; label: string }[] = [];
    let currentX = 0;

    sections.forEach((section) => {
      const duration = section.blocks.reduce((sum, b) => sum + (b.duration || 0), 0) / 60;
      const energy = sectionEnergies[section.label.toLowerCase()] || 0.5;

      points.push({ x: currentX, y: energy, label: section.label });
      currentX += duration;
      points.push({ x: currentX, y: energy, label: section.label });
    });

    if (points.length < 2) return;

    const maxX = Math.max(...points.map((p) => p.x), 1);
    const scaleX = (x: number) => padding + (x / maxX) * (width - 2 * padding);
    const scaleY = (y: number) => height - padding - y * (height - 2 * padding);

    // Draw gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, 'rgba(45, 90, 71, 0.3)');
    gradient.addColorStop(1, 'rgba(45, 90, 71, 0.05)');

    ctx.beginPath();
    ctx.moveTo(scaleX(points[0].x), scaleY(0));
    points.forEach((p) => ctx.lineTo(scaleX(p.x), scaleY(p.y)));
    ctx.lineTo(scaleX(points[points.length - 1].x), scaleY(0));
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw line
    ctx.beginPath();
    ctx.moveTo(scaleX(points[0].x), scaleY(points[0].y));
    points.forEach((p) => ctx.lineTo(scaleX(p.x), scaleY(p.y)));
    ctx.strokeStyle = '#2D5A47';
    ctx.lineWidth = 3;
    ctx.stroke();

    // Labels
    ctx.fillStyle = '#6D6D6D';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('0 min', padding, height - 10);
    ctx.fillText(`${Math.round(maxX)} min`, width - padding, height - 10);
    ctx.fillText('Energy', padding, 15);
  }

  onMount(() => {
    if (sections.length > 0) drawChart();
  });
</script>

<div class:compact class="energy-chart">
  <canvas
    bind:this={canvas}
    width={compact ? 260 : 400}
    height={compact ? 90 : 150}
    aria-label={chartLabel}
  ></canvas>
</div>

<style>
  .energy-chart {
    background: var(--color-surface);
    border-radius: var(--radius-md);
    padding: 16px;
  }

  .energy-chart.compact {
    padding: 12px;
  }

  canvas {
    width: 100%;
    height: auto;
  }
</style>
