/**
 * Shared throttling and topology tracking for Mapbox GeoJSON updates.
 * Loaded before static/script.js; no emojis in this file.
 */
(function (global) {
    'use strict';

    var VEHICLE_MAP_MAX_FPS = 15;
    var minFrameMs = 1000 / VEHICLE_MAP_MAX_FPS;

    global.MapRenderScheduler = {
        VEHICLE_MAP_MAX_FPS: VEHICLE_MAP_MAX_FPS,
        minFrameMs: minFrameMs,
        lastTopologyRendered: -1
    };
})(typeof window !== 'undefined' ? window : globalThis);
