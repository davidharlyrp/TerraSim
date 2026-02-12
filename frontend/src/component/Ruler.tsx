import React, { useState, useMemo } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import { Line, Text } from '@react-three/drei';
import { useTheme } from '../context/ThemeContext';
import * as THREE from 'three';

export const Ruler: React.FC = () => {
    const { camera, size } = useThree();
    const { theme } = useTheme();
    const [view, setView] = useState({
        left: 0, right: 0, top: 0, bottom: 0, zoom: 20,
        camX: 0, camY: 0
    });

    useFrame(() => {
        if (camera instanceof THREE.OrthographicCamera) {
            const zoom = camera.zoom;
            const width = size.width / zoom;
            const height = size.height / zoom;
            const left = camera.position.x - width / 2;
            const right = camera.position.x + width / 2;
            const top = camera.position.y + height / 2;
            const bottom = camera.position.y - height / 2;

            // Update every frame for perfect sync during pan/zoom
            if (view.left !== left || view.top !== top || view.zoom !== zoom) {
                setView({ left, right, top, bottom, zoom, camX: camera.position.x, camY: camera.position.y });
            }
        }
    });

    const { xTicks, yTicks } = useMemo(() => {
        const zoom = view.zoom;
        const targetPixels = 100; // Aim for ~100px between labels
        const idealSpacing = targetPixels / zoom;

        // 1-2-5 spacing algorithm
        const log = Math.log10(idealSpacing);
        const power = Math.floor(log);
        const base = Math.pow(10, power);
        const factor = idealSpacing / base;

        let spacing;
        if (factor < 1.5) spacing = base;
        else if (factor < 3.5) spacing = base * 2;
        else if (factor < 7.5) spacing = base * 5;
        else spacing = base * 10;

        const xTicks = [];
        const startX = Math.floor(view.left / spacing) * spacing;
        const endX = Math.ceil(view.right / spacing) * spacing;
        for (let x = startX; x <= endX; x += spacing) {
            xTicks.push(x);
        }

        const yTicks = [];
        const startY = Math.floor(view.bottom / spacing) * spacing;
        const endY = Math.ceil(view.top / spacing) * spacing;
        for (let y = startY; y <= endY; y += spacing) {
            yTicks.push(y);
        }

        return { xTicks, yTicks, spacing };
    }, [view.left, view.right, view.top, view.bottom, view.zoom]);

    const labelSize = 12 / view.zoom;
    const axisOffset = 18 / view.zoom;
    const tickLen = 6 / view.zoom;

    // Fixed edge positions
    const horizontalRulerY = view.top - axisOffset;
    const verticalRulerX = view.right - axisOffset;

    const rulerColor = theme === 'dark' ? "#ffffff" : "#28292a";

    return (
        <group>
            {/* Horizontal Axis Bar */}
            <Line
                points={[[view.left, horizontalRulerY, 10], [view.right, horizontalRulerY, 10]]}
                color={rulerColor}
                lineWidth={2}
            />
            {xTicks.map(x => (
                <group key={`x-${x}`}>
                    <Line
                        points={[[x, horizontalRulerY, 10], [x, horizontalRulerY - tickLen, 10]]}
                        color={rulerColor}
                        lineWidth={2}
                    />
                    <Text
                        position={[x, horizontalRulerY - tickLen * 1.5, 10]}
                        fontSize={labelSize}
                        color={rulerColor}
                        anchorX="center"
                        anchorY="top"
                    >
                        {parseFloat(x.toFixed(3)).toString()}
                    </Text>
                </group>
            ))}

            {/* Vertical Axis Bar */}
            <Line
                points={[[verticalRulerX, view.bottom, 10], [verticalRulerX, view.top, 10]]}
                color={rulerColor}
                lineWidth={2}
            />
            {yTicks.map(y => (
                <group key={`y-${y}`}>
                    <Line
                        points={[[verticalRulerX, y, 10], [verticalRulerX - tickLen, y, 10]]}
                        color={rulerColor}
                        lineWidth={2}
                    />
                    <Text
                        position={[verticalRulerX - tickLen * 1.5, y, 10]}
                        fontSize={labelSize}
                        color={rulerColor}
                        anchorX="right"
                        anchorY="middle"
                    >
                        {parseFloat(y.toFixed(3)).toString()}
                    </Text>
                </group>
            ))}

            {/* Axis Identification Labels */}
            {/* <Text
                position={[view.right - labelSize, horizontalRulerY + labelSize, 0.9]}
                fontSize={labelSize * 1.5}
                color="#60a5fa"
                anchorX="right"
                anchorY="bottom"
                fontWeight="bold"
            >
                X (m)
            </Text>
            <Text
                position={[verticalRulerX + labelSize, view.top - labelSize, 0.9]}
                fontSize={labelSize * 1.5}
                color="#60a5fa"
                anchorX="right"
                anchorY="top"
                fontWeight="bold"
                rotation={[0, 0, -Math.PI / 2]}
            >
                Y (m)
            </Text> */}
        </group>
    );
};

