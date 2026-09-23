import React, { useState, useMemo, useRef } from 'react';
import { formatINR } from '../utils/formatters';

import { GraphSkeleton } from './Skeletons';

const TIME_FILTERS = ['1M', '2M', '6M', '12M', '24M', '5Y'];

export default function WealthGraph({
  currentTotal = 0,
  snapshots = [],
  hasSufficientHistory = false,
  activeTimeframe = '1M',
  onTimeframeChange,
  isLoading = false
}) {
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const containerRef = useRef(null);

  // Format real snapshot points for SVG rendering
  const points = useMemo(() => {
    if (!snapshots || snapshots.length === 0) return [];
    return snapshots.map((s, idx) => {
      const d = new Date(s.snapshot_date || s.date);
      const day = d.getDate();
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const month = months[d.getMonth()];
      const displayDate = `${day} ${month}`;

      return {
        index: idx,
        rawDate: s.snapshot_date || s.date,
        displayDate,
        value: s.value || s.total_value,
        isToday: idx === snapshots.length - 1
      };
    });
  }, [snapshots]);

  // Compute chart coordinates
  const { minVal, maxVal, pathD, areaD, pointCoords } = useMemo(() => {
    if (!points || points.length < 2) {
      return { minVal: 0, maxVal: 0, pathD: '', areaD: '', pointCoords: [] };
    }

    const values = points.map(p => p.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.12 || 1000;
    const yMin = Math.max(0, min - padding);
    const yMax = max + padding;

    const width = 800;
    const height = 240;
    const padX = 15;
    const padY = 20;

    const coords = points.map((p, idx) => {
      const x = padX + (idx / (points.length - 1)) * (width - 2 * padX);
      const y = height - padY - ((p.value - yMin) / (yMax - yMin)) * (height - 2 * padY);
      return { x, y, point: p };
    });

    // Cubic bezier path
    let d = `M ${coords[0].x} ${coords[0].y}`;
    for (let i = 0; i < coords.length - 1; i++) {
      const current = coords[i];
      const next = coords[i + 1];
      const controlX = (current.x + next.x) / 2;
      d += ` C ${controlX} ${current.y}, ${controlX} ${next.y}, ${next.x} ${next.y}`;
    }

    const area = `${d} L ${coords[coords.length - 1].x} ${height} L ${coords[0].x} ${height} Z`;

    return {
      minVal: min,
      maxVal: max,
      pathD: d,
      areaD: area,
      pointCoords: coords,
    };
  }, [points]);

  // Handle pointer tracking
  const handleMouseMove = (e) => {
    if (!containerRef.current || pointCoords.length === 0) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, clientX / rect.width));

    const targetIdx = Math.round(ratio * (pointCoords.length - 1));
    const nearest = pointCoords[targetIdx];
    if (nearest) {
      setHoveredPoint({
        ...nearest,
        containerX: (nearest.x / 800) * rect.width,
        containerY: (nearest.y / 240) * rect.height,
      });
    }
  };

  const handleMouseLeave = () => {
    setHoveredPoint(null);
  };

  return (
    <section className="graph-card" aria-label="Total Wealth Over Time">
      <div className="graph-header">
        <div className="graph-title-group">
          <span className="graph-title">TOTAL WEALTH OVER TIME</span>
          {hoveredPoint ? (
            <span className="graph-hover-readout">
              {hoveredPoint.point.displayDate}: <strong>{formatINR(hoveredPoint.point.value)}</strong>
            </span>
          ) : (
            <span className="graph-hover-readout">
              Today: <strong>{formatINR(currentTotal)}</strong>
            </span>
          )}
        </div>

        {/* Time Filters */}
        <div className="time-filters" role="tablist">
          {TIME_FILTERS.map(tf => (
            <button
              key={tf}
              role="tab"
              aria-selected={activeTimeframe === tf}
              className={`time-btn ${activeTimeframe === tf ? 'active' : ''}`}
              onClick={() => {
                if (onTimeframeChange) onTimeframeChange(tf);
                setHoveredPoint(null);
              }}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Main Chart or Clean History Empty State */}
      {isLoading ? (
        <GraphSkeleton />
      ) : !hasSufficientHistory || pointCoords.length < 2 ? (
        <div
          style={{
            height: 240,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(255, 255, 255, 0.015)',
            border: '1px dashed var(--border, rgba(255, 255, 255, 0.1))',
            borderRadius: '8px',
            color: 'var(--text-muted, #94a3b8)',
            textAlign: 'center',
            padding: '24px'
          }}
        >
          <div style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-primary, #f8fafc)', marginBottom: 6 }}>
            Not enough history yet.
          </div>
          <div style={{ fontSize: '0.85rem', maxWidth: 360, lineHeight: 1.4 }}>
            Historical portfolio points will automatically appear as daily snapshots accumulate over time.
          </div>
        </div>
      ) : (
        <div
          className="chart-container"
          ref={containerRef}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <svg
            className="chart-svg"
            viewBox="0 0 800 240"
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id="wealthGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.12" />
                <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            <line x1="15" y1="70" x2="785" y2="70" className="chart-axis-line" />
            <line x1="15" y1="160" x2="785" y2="160" className="chart-axis-line" />

            <path d={areaD} className="chart-area" />
            <path d={pathD} className="chart-line" />

            {hoveredPoint && (
              <g>
                <line
                  x1={hoveredPoint.x}
                  y1="10"
                  x2={hoveredPoint.x}
                  y2="230"
                  className="chart-hover-line"
                />
                <circle
                  cx={hoveredPoint.x}
                  cy={hoveredPoint.y}
                  r="4.5"
                  className="chart-hover-point"
                />
              </g>
            )}
          </svg>

          {hoveredPoint && (
            <div
              className="chart-tooltip"
              style={{
                left: `${hoveredPoint.containerX}px`,
                top: `${hoveredPoint.containerY}px`,
              }}
            >
              <div className="tooltip-date">{hoveredPoint.point.displayDate}</div>
              <div className="tooltip-val">{formatINR(hoveredPoint.point.value)}</div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
