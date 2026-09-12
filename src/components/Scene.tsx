'use client';
'use no memo';

import { Canvas, useFrame } from '@react-three/fiber';
import { Environment, Float, PresentationControls, useGLTF } from '@react-three/drei';
import { useRef, useState, useMemo, useEffect } from 'react';
import * as THREE from 'three';

function MonsterCan() {
  const group = useRef<THREE.Group>(null);
  // Load the GLB file with textures and materials built-in
  const gltf = useGLTF(`/model/white_monster_converted.glb`);

  // Calculate bounding box, scale, and centering offset
  const { scale, centerOffset, isZUp } = useMemo(() => {
    const bbox = new THREE.Box3().setFromObject(gltf.scene);
    const size = new THREE.Vector3();
    bbox.getSize(size);
    
    const center = new THREE.Vector3();
    bbox.getCenter(center);
    
    // Scale model down slightly so it doesn't clip the edges of the container
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale = 5.8 / maxDim;
    
    // Detect if the model was exported laying on its side
    const isZUp = size.z > size.y;
    
    return { 
      scale, 
      centerOffset: center.multiplyScalar(-1), // Shift it back to exactly [0,0,0]
      isZUp
    };
  }, [gltf.scene]);

  const time = useRef(0);
  useFrame((_, delta) => {
    time.current += delta;
    if (group.current) {
      // Continuous slow rotation to show off the 3D shape and textures
      group.current.rotation.y = time.current * 0.5;
      group.current.rotation.z = Math.cos(time.current * 0.3) * 0.05;
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.2} floatIntensity={1.5}>
      <group ref={group} position={[0, 0, 0]}>
        {/* Scale the wrapper and optionally rotate it upright if it was Z-up */}
        <group 
          scale={[scale, scale, scale]} 
          rotation={isZUp ? [-Math.PI / 2, 0, 0] : [0, 0, 0]}
        >
          {/* Offset the raw scene so its true center is at local [0,0,0] */}
          <primitive 
            object={gltf.scene} 
            position={[centerOffset.x, centerOffset.y, centerOffset.z]} 
            dispose={null}
          />
        </group>
      </group>
    </Float>
  );
}

// Preload the GLB so it's ready instantly
if (typeof window !== 'undefined') {
  useGLTF.preload(`/model/white_monster_converted.glb`);
}

function ParticleField() {
  const count = 150;
  const mesh = useRef<THREE.InstancedMesh>(null);

  const dummy = useMemo(() => new THREE.Object3D(), []);

  // Use useState with lazy initializer to avoid calling Math.random during render
  const [particles] = useState(() => {
    const temp = [];
    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * 20;
      const y = (Math.random() - 0.5) * 20;
      const z = (Math.random() - 0.5) * 20 - 5;
      const factor = Math.random() * 0.5 + 0.5;
      const speed = Math.random() * 0.01 + 0.005;
      temp.push({ x, y, z, factor, speed });
    }
    return temp;
  });

  const timeRef = useRef(0);
  useFrame((_, delta) => {
    timeRef.current += delta;
    particles.forEach((particle, i) => {
      // Floating up effect like bubbles in energy drink
      particle.y += particle.speed;
      if (particle.y > 10) particle.y = -10;

      dummy.position.set(particle.x, particle.y, particle.z);

      // Gentle wobble
      const time = timeRef.current;
      dummy.rotation.x = Math.sin(time * particle.factor) * 0.2;
      dummy.rotation.y = Math.cos(time * particle.factor) * 0.2;
      dummy.rotation.z = Math.sin(time * particle.factor) * 0.2;

      const s = particle.factor * 0.05;
      dummy.scale.set(s, s, s);

      dummy.updateMatrix();
      mesh.current?.setMatrixAt(i, dummy.matrix);
    });
    mesh.current!.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, count]}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshStandardMaterial color="#cccccc" transparent opacity={0.3} metalness={0.5} roughness={0.2} />
    </instancedMesh>
  );
}

export default function Scene() {
  return (
    <div id="canvas-container" style={{ width: '100%', height: '100%' }}>
      <Canvas 
        camera={{ position: [0, 0, 8], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ antialias: false }}
      >
        {/* Transparent background to blend with Bento Cell */}

        {/* Softened lighting to prevent blown out textures and harsh specular lines */}
        <ambientLight intensity={0.8} color="#ffffff" />
        <directionalLight position={[5, 10, 5]} intensity={1.5} castShadow color="#ffffff" />
        <pointLight position={[-10, -10, -10]} intensity={0.5} color="#f0f0f0" />

        <PresentationControls
          global
          rotation={[0, 0, 0]}
          polar={[-Math.PI / 4, Math.PI / 4]}
          azimuth={[-Math.PI / 1.4, Math.PI / 2]}
        >
          <MonsterCan />
        </PresentationControls>

        {/* Keep particles but make them a subtle silver/white */}
        <ParticleField />

        {/* 'city' preset provides much softer, diffuse reflections compared to 'studio' */}
        <Environment preset="city" resolution={128} />
      </Canvas>
    </div>
  );
}
