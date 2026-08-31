'use client';

import {
  type CSSProperties,
  type MouseEventHandler,
  type ReactNode,
  useEffect,
  useRef,
} from 'react';
import { Color, Mesh, Program, Renderer, Triangle } from 'ogl';
import './SpecularButton.css';

const PAD = 20;
const VERT = `#version 300 es
in vec2 position;
void main(){gl_Position=vec4(position,0.0,1.0);}`;
const FRAG = `#version 300 es
precision highp float;
uniform vec2 uCenter; uniform vec2 uHalfSize; uniform float uRadius; uniform float uAngle;
uniform float uPx; uniform vec3 uLineColor; uniform vec3 uBaseColor; uniform float uIntensity;
uniform float uShineSize; uniform float uShineFade; uniform float uThickness; uniform float uBaseWidth;
out vec4 fragColor;
float sdRoundedRect(vec2 p,vec2 b,float r){vec2 q=abs(p)-b+r;return length(max(q,0.0))+min(max(q.x,q.y),0.0)-r;}
void main(){vec2 p=gl_FragCoord.xy-uCenter;float d=sdRoundedRect(p,uHalfSize,uRadius);vec2 L=vec2(cos(uAngle),sin(uAngle));float base=(1.0-smoothstep(0.0,uBaseWidth,abs(d)))*0.8;vec2 nEll=normalize(p/(uHalfSize*uHalfSize)+1e-6);float phi=acos(clamp(abs(dot(nEll,L)),0.0,1.0));float rim=1.0-smoothstep(uShineSize-uShineFade,uShineSize+uShineFade+1e-4,phi);float x=d/(uThickness+1e-6);float line=exp(-mix(1.0,1.6,smoothstep(0.0,1.5,x))*x*x);float edgeClamp=1.0-smoothstep(0.5*uPx,3.0*uPx,abs(d));float hi=line*rim*edgeClamp*uIntensity;vec3 col=uBaseColor*base+uLineColor*hi;fragColor=vec4(col,clamp(base+hi,0.0,1.0));}`;

type Props = {
  children: ReactNode;
  className?: string;
  onClick?: MouseEventHandler<HTMLButtonElement>;
  lineColor?: string;
  baseColor?: string;
  radius?: number;
};

export default function SpecularButton({
  children,
  className = '',
  onClick,
  lineColor = '#f59e0b',
  baseColor = '#f59e0b',
  radius = 8,
}: Props) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const effectRef = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const button = buttonRef.current,
      effect = effectRef.current;
    if (!button || !effect) return;
    const dpr = window.devicePixelRatio || 1,
      renderer = new Renderer({
        alpha: true,
        premultipliedAlpha: true,
        antialias: true,
        dpr,
      }),
      gl = renderer.gl;
    gl.clearColor(0, 0, 0, 0);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    const geometry = new Triangle(gl);
    if (geometry.attributes.uv) delete geometry.attributes.uv;
    const program = new Program(gl, {
      vertex: VERT,
      fragment: FRAG,
      uniforms: {
        uCenter: { value: [0, 0] },
        uHalfSize: { value: [1, 1] },
        uRadius: { value: radius * dpr },
        uAngle: { value: 2.4 },
        uPx: { value: dpr },
        uLineColor: { value: [1, 1, 1] },
        uBaseColor: { value: [1, 1, 1] },
        uIntensity: { value: 1 },
        uShineSize: { value: 0.2 },
        uShineFade: { value: 0.7 },
        uThickness: { value: 1.5 * dpr },
        uBaseWidth: { value: 1.2 * dpr },
      },
    });
    const mesh = new Mesh(gl, { geometry, program });
    effect.appendChild(gl.canvas);
    const size = { w: 1, h: 1 };
    const resize = () => {
      const rect = button.getBoundingClientRect();
      size.w = rect.width;
      size.h = rect.height;
      renderer.setSize(rect.width + PAD * 2, rect.height + PAD * 2);
      program.uniforms.uCenter.value = [
        (PAD + rect.width / 2) * dpr,
        (PAD + rect.height / 2) * dpr,
      ];
      program.uniforms.uHalfSize.value = [
        (rect.width / 2) * dpr,
        (rect.height / 2) * dpr,
      ];
    };
    const observer = new ResizeObserver(resize);
    observer.observe(button);
    resize();
    let pointerAngle = 2.4,
      proximity = 0;
    const move = (event: PointerEvent) => {
      const rect = button.getBoundingClientRect(),
        cx = rect.left + rect.width / 2,
        cy = rect.top + rect.height / 2,
        dx = Math.max(rect.left - event.clientX, 0, event.clientX - rect.right),
        dy = Math.max(rect.top - event.clientY, 0, event.clientY - rect.bottom),
        distance = Math.hypot(dx, dy);
      pointerAngle = Math.atan2(cy - event.clientY, event.clientX - cx);
      const t = Math.max(0, 1 - distance / 250);
      proximity = t * t * (3 - 2 * t);
    };
    window.addEventListener('pointermove', move);
    const line = new Color(lineColor),
      base = new Color(baseColor);
    program.uniforms.uLineColor.value = [line.r, line.g, line.b];
    program.uniforms.uBaseColor.value = [base.r, base.g, base.b];
    let angle = 2.4,
      brightness = 0,
      last = performance.now(),
      frame = 0;
    const update = (now: number) => {
      frame = requestAnimationFrame(update);
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      const diff =
        ((pointerAngle - angle + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
      angle += diff * (1 - Math.exp(-dt * 7));
      brightness += (proximity - brightness) * (1 - Math.exp(-dt * 8));
      program.uniforms.uAngle.value = angle;
      program.uniforms.uRadius.value =
        Math.min(radius, Math.min(size.w, size.h) / 2) * dpr;
      program.uniforms.uIntensity.value = 0.85 + 1.4 * brightness;
      renderer.render({ scene: mesh });
    };
    frame = requestAnimationFrame(update);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener('pointermove', move);
      gl.canvas.remove();
      gl.getExtension('WEBGL_lose_context')?.loseContext();
    };
  }, [baseColor, lineColor, radius]);
  return (
    <button
      ref={buttonRef}
      type="button"
      onClick={onClick}
      className={`specular-button ${className}`}
      style={{ '--sb-radius': `${radius}px` } as CSSProperties}
    >
      <span
        ref={effectRef}
        className="specular-button__fx"
        aria-hidden="true"
      />
      <span className="specular-button__label">{children}</span>
    </button>
  );
}
