'use client';
import { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import { globalSpills } from '../../data/demoIncident';
import 'maplibre-gl/dist/maplibre-gl.css';

export default function GlobalSpillMap({
  onSelect,
}: {
  onSelect: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const selectRef = useRef(onSelect);
  useEffect(() => {
    selectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    if (!container.current) return;
    const markers: maplibregl.Marker[] = [];
    const map = new maplibregl.Map({
      container: container.current,
      center: [45, 15],
      zoom: 1.25,
      minZoom: 1,
      maxZoom: 7,
      attributionControl: false,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap contributors',
          },
        },
        layers: [
          {
            id: 'world-base',
            type: 'raster',
            source: 'osm',
            paint: {
              'raster-saturation': -1,
              'raster-brightness-min': 0.035,
              'raster-brightness-max': 0.42,
              'raster-contrast': 0.42,
            },
          },
        ],
      },
    });
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      'top-right',
    );
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      'bottom-right',
    );

    map.once('load', () => {
      map.resize();
      globalSpills.forEach((spill) => {
        const element = document.createElement('button');
        element.type = 'button';
        element.className = `global-spill-marker severity-${spill.severity.toLowerCase()} ${spill.ready ? 'ready' : ''}`;
        element.setAttribute('aria-label', `${spill.name}, ${spill.status}`);
        element.innerHTML = `<i></i><span>#${spill.id}</span>`;
        element.addEventListener('click', (event) => {
          event.stopPropagation();
          selectRef.current(spill.id);
        });
        const popup = new maplibregl.Popup({
          offset: 16,
          closeButton: false,
          className: 'global-popup',
        }).setHTML(
          `<small>${spill.severity} PRIORITY</small><strong>${spill.name}</strong><span>${spill.location}</span><b>${spill.status}</b>`,
        );
        markers.push(
          new maplibregl.Marker({ element, anchor: 'center' })
            .setLngLat(spill.coordinate)
            .setPopup(popup)
            .addTo(map),
        );
      });
      requestAnimationFrame(() => map.resize());
    });

    const resize = () => requestAnimationFrame(() => map.resize());
    window.addEventListener('resize', resize, { passive: true });
    return () => {
      window.removeEventListener('resize', resize);
      markers.forEach((marker) => marker.remove());
      map.remove();
    };
  }, []);
  return <div ref={container} className="global-map" />;
}
