import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function ThreeGem() {
  const mountRef = useRef(null);

  useEffect(() => {
    const stage = mountRef.current;
    if (!stage) return;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(stage.clientWidth, stage.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    stage.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, stage.clientWidth / stage.clientHeight, 0.1, 100);
    camera.position.set(0, 0, 4.4);

    const group = new THREE.Group();
    const geo = new THREE.IcosahedronGeometry(1.3, 0);
    
    const solid = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
      color: 0x2a0008, emissive: 0x5a0010, flatShading: true, metalness: 0.3, roughness: 0.35
    }));
    
    const wire = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: 0xff0a2c, wireframe: true }));
    wire.scale.set(1.02, 1.02, 1.02);
    
    group.add(solid, wire);
    scene.add(group);

    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const p1 = new THREE.PointLight(0xff0a2c, 2.2, 12); 
    p1.position.set(3, 2, 3); 
    scene.add(p1);
    
    const p2 = new THREE.PointLight(0xffcb05, 1.2, 12); 
    p2.position.set(-3, -2, 2); 
    scene.add(p2);

    let dragging = false, lastX = 0, lastY = 0, dragRotX = 0, dragRotY = 0;
    let hoverTiltX = 0, hoverTiltY = 0, driftX = 0, autoY = 0;

    const onResize = () => {
      if(!stage) return;
      const w = stage.clientWidth, h = stage.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener('resize', onResize);

    const onMouseMoveStage = (e) => {
      if (dragging) return;
      const r = stage.getBoundingClientRect();
      hoverTiltX = ((e.clientY - r.top) / r.height - 0.5) * 0.5;
      hoverTiltY = ((e.clientX - r.left) / r.width - 0.5) * 0.6;
    };
    const onMouseLeaveStage = () => { hoverTiltX = 0; hoverTiltY = 0; };
    const onMouseDown = (e) => { dragging = true; lastX = e.clientX; lastY = e.clientY; };
    const onMouseMoveWindow = (e) => {
      if (!dragging) return;
      dragRotY += (e.clientX - lastX) * 0.008;
      dragRotX += (e.clientY - lastY) * 0.008;
      lastX = e.clientX; lastY = e.clientY;
    };
    const onMouseUp = () => { dragging = false; };

    stage.addEventListener('mousemove', onMouseMoveStage);
    stage.addEventListener('mouseleave', onMouseLeaveStage);
    renderer.domElement.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMoveWindow);
    window.addEventListener('mouseup', onMouseUp);

    let animationFrameId;
    const lerp = (a, b, t) => a + (b - a) * t;

    const animate = () => {
      if (!dragging) autoY += 0.0045;
      driftX = lerp(driftX, hoverTiltX, 0.06);
      group.rotation.x = driftX + dragRotX;
      group.rotation.y = autoY + hoverTiltY + dragRotY;
      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('mousemove', onMouseMoveWindow);
      window.removeEventListener('mouseup', onMouseUp);
      if(stage) {
          stage.removeEventListener('mousemove', onMouseMoveStage);
          stage.removeEventListener('mouseleave', onMouseLeaveStage);
          if (stage.contains(renderer.domElement)) {
            stage.removeChild(renderer.domElement);
          }
      }
      renderer.domElement.removeEventListener('mousedown', onMouseDown);
      geo.dispose();
      solid.material.dispose();
      wire.material.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%', minHeight: '400px' }}>
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 50% 50%, rgba(255,10,44,.35), transparent 65%)', filter: 'blur(10px)', pointerEvents: 'none' }}></div>
      <div ref={mountRef} style={{ position: 'relative', width: '100%', height: '100%', filter: 'drop-shadow(0 0 36px rgba(255,10,44,.45))', cursor: 'grab' }}></div>
    </div>
  );
}
