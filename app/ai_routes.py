from __future__ import annotations

import asyncio
from datetime import datetime

from flask import Blueprint, jsonify, request

bp = Blueprint("ai", __name__)

_ai_chatbot = None
_active_chatbot = None
_ultra_chatbot = None
_integrated_system = None
_sumo_manager = None
_system_state = None
_select_chatbot = None

ai_map_focus_data = None


def init_ai_routes(
    ai_chatbot,
    active_chatbot,
    ultra_chatbot,
    integrated_system,
    sumo_manager,
    system_state,
    select_chatbot_fn,
):
    global _ai_chatbot, _active_chatbot, _ultra_chatbot
    global _integrated_system, _sumo_manager, _system_state, _select_chatbot
    _ai_chatbot = ai_chatbot
    _active_chatbot = active_chatbot
    _ultra_chatbot = ultra_chatbot
    _integrated_system = integrated_system
    _sumo_manager = sumo_manager
    _system_state = system_state
    _select_chatbot = select_chatbot_fn


@bp.route("/api/ai/advice", methods=["GET", "POST"])
def ai_advice():
    """Generate AI advice using the chatbot system."""
    try:
        q = request.args.get("q")
        if request.method == "POST":
            body = request.get_json(silent=True) or {}
            q = q or body.get("question")

        if not q:
            q = (
                "Provide insights and recommendations for grid optimization,"
                " V2G opportunities, and system improvements."
            )

        response = _ai_chatbot.process_message(q, user_id="api_user")

        return jsonify({
            "advice": response["text"],
            "type": response.get("type", "response"),
            "intent": response.get("intent", "general"),
            "timestamp": response.get("timestamp", datetime.now().isoformat()),
            "data": response.get("data", {}),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ai/report")
def ai_report():
    """Generate comprehensive AI report."""
    try:
        response = _ai_chatbot.generate_system_report()
        return jsonify({
            "report": response["text"],
            "summary": response.get("summary", {}),
            "recommendations": response.get("recommendations", []),
            "timestamp": response.get("timestamp", datetime.now().isoformat()),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ai/v2g/optimize", methods=["POST"])
def ai_v2g_optimize():
    """AI-powered V2G optimization recommendations."""
    try:
        body = request.get_json() or {}
        optimization_type = body.get("type", "general")
        response = _ai_chatbot.get_v2g_optimization(optimization_type)

        return jsonify({
            "optimization": response["text"],
            "recommendations": response.get("recommendations", []),
            "potential_savings": response.get("potential_savings", {}),
            "timestamp": response.get("timestamp", datetime.now().isoformat()),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ai/predict", methods=["POST"])
def ai_predict():
    """AI-powered predictions for grid operations."""
    try:
        body = request.get_json() or {}
        prediction_type = body.get("type", "demand")
        timeframe = body.get("timeframe", "1h")
        response = _ai_chatbot.get_predictions(prediction_type, timeframe)

        return jsonify({
            "predictions": response["text"],
            "data": response.get("data", {}),
            "confidence": response.get("confidence", 0.85),
            "timestamp": response.get("timestamp", datetime.now().isoformat()),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    """AI chat - agentic tool-calling with fallback chain."""
    try:
        body = request.get_json() or {}
        message = body.get("message", "")
        user_id = body.get("user_id", "web_user")

        if not message:
            return jsonify({"error": "Message is required"}), 400

        if _active_chatbot.is_available():
            print(f"[API /ai/chat] -> {type(_active_chatbot).__name__}: {message}")
            try:
                ai_response = asyncio.run(_active_chatbot.chat(message, user_id=user_id))

                if isinstance(ai_response, dict) and ai_response.get("fallback"):
                    fallback = _select_chatbot(
                        agentic_chatbot=None,
                        ultra_chatbot=_ultra_chatbot,
                        ai_chatbot=_ai_chatbot,
                    )
                    ai_response = asyncio.run(fallback.chat(message, user_id=user_id))

                response_text = (
                    ai_response.get("text", "") if isinstance(ai_response, dict) else str(ai_response)
                )
                return jsonify({
                    "status": "success",
                    "response": response_text,
                    "full_data": ai_response,
                })
            except Exception as e:
                print(f"[API /ai/chat] Chatbot error: {e}")
                import traceback

                traceback.print_exc()

        return jsonify({
            "text": "No AI system available. Please check configuration.",
            "type": "error",
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ai/enhanced/status")
def ai_enhanced_status():
    """Get enhanced AI system status and capabilities."""
    try:
        status = _ai_chatbot.get_ai_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ai/enhanced/visual", methods=["POST"])
def ai_visual_analysis():
    """Analyze visual map data."""
    try:
        map_data = _integrated_system.get_network_state()

        if _system_state["sumo_running"] and _sumo_manager.running:
            vehicles = []
            try:
                import traci

                for vehicle in _sumo_manager.vehicles.values():
                    if vehicle.id in traci.vehicle.getIDList():
                        x, y = traci.vehicle.getPosition(vehicle.id)
                        lon, lat = traci.simulation.convertGeo(x, y)
                        vehicles.append({
                            "id": vehicle.id,
                            "lat": lat,
                            "lon": lon,
                            "type": vehicle.config.vtype.value,
                            "speed": vehicle.speed,
                            "soc": vehicle.config.current_soc if vehicle.config.is_ev else 1.0,
                        })
            except Exception:
                vehicles = []
            map_data["vehicles"] = vehicles

        visual_analysis = _ai_chatbot.visual_processor.analyze_map_state(map_data)

        return jsonify({
            "visual_analysis": visual_analysis,
            "timestamp": datetime.now().isoformat(),
            "map_data_processed": True,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ai/enhanced/multimodal", methods=["POST"])
def ai_multimodal_processing():
    """Process multi-modal input (text, image, voice)."""
    try:
        text_input = request.form.get("text", "")

        image_data = None
        if "image" in request.files:
            image_file = request.files["image"]
            if image_file:
                image_data = image_file.read()

        voice_data = None
        if "voice" in request.files:
            voice_file = request.files["voice"]
            if voice_file:
                voice_data = voice_file.read()

        result = _ai_chatbot.process_multimodal_input(text_input, image_data, voice_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ai/enhanced/conversation/<user_id>")
def ai_conversation_intelligence(user_id):
    """Get conversation intelligence for a specific user."""
    try:
        intelligence = _ai_chatbot.get_conversation_intelligence(user_id)
        return jsonify(intelligence)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ai/enhanced/performance")
def ai_performance_metrics():
    """Get AI system performance metrics and learning insights."""
    try:
        performance = _ai_chatbot.performance_tracker.get_performance_metrics()
        learning = _ai_chatbot.learning_engine.get_learning_insights()

        return jsonify({
            "performance_metrics": performance,
            "learning_insights": learning,
            "system_health": "optimal",
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/map/focus", methods=["POST"])
def focus_map():
    """Focus map on specific location with real-time updates."""
    global ai_map_focus_data
    try:
        body = request.get_json() or {}
        location = body.get("location", "")
        zoom = body.get("zoom", 16)
        action_type = body.get("action_type", "focus")

        if not location:
            return jsonify({"error": "Location is required"}), 400

        locations = {
            "times_square": {"lat": 40.7580, "lon": -73.9855, "name": "Times Square"},
            "penn_station": {"lat": 40.7505, "lon": -73.9934, "name": "Penn Station"},
            "grand_central": {"lat": 40.7527, "lon": -73.9772, "name": "Grand Central"},
            "columbus_circle": {"lat": 40.7681, "lon": -73.9819, "name": "Columbus Circle"},
            "union_square": {"lat": 40.7359, "lon": -73.9911, "name": "Union Square"},
            "washington_square": {"lat": 40.7308, "lon": -73.9973, "name": "Washington Square"},
            "brooklyn_bridge": {"lat": 40.7061, "lon": -73.9969, "name": "Brooklyn Bridge"},
            "wall_street": {"lat": 40.7074, "lon": -74.0113, "name": "Wall Street"},
            "central_park": {"lat": 40.7829, "lon": -73.9654, "name": "Central Park"},
            "manhattan": {"lat": 40.7831, "lon": -73.9712, "name": "Manhattan Overview"},
        }

        location_key = location.lower().replace(" ", "_")
        coords = None
        for key, loc_info in locations.items():
            if key in location_key or location_key in key:
                coords = loc_info
                break

        if not coords:
            return jsonify({
                "error": f'Location "{location}" not found',
                "available_locations": list(locations.keys()),
            }), 404

        infrastructure_data: dict = {
            "substations": [],
            "ev_stations": [],
            "traffic_lights": [],
        }

        if hasattr(_integrated_system, "substations"):
            for sub_id, substation in _integrated_system.substations.items():
                infrastructure_data["substations"].append({
                    "id": sub_id,
                    "name": substation.get("name", sub_id),
                    "lat": substation.get("lat"),
                    "lon": substation.get("lon"),
                    "operational": substation.get("operational", True),
                    "voltage_kv": substation.get("voltage_kv", 138),
                })

        if hasattr(_integrated_system, "ev_stations"):
            for station_id, station in _integrated_system.ev_stations.items():
                infrastructure_data["ev_stations"].append({
                    "id": station_id,
                    "name": station.get("name", station_id),
                    "lat": station.get("lat"),
                    "lon": station.get("lon"),
                    "operational": station.get("operational", True),
                    "ports_available": 20,
                })

        ai_map_focus_data = {
            "location": coords["name"],
            "lat": coords["lat"],
            "lon": coords["lon"],
            "zoom": zoom,
            "action_type": action_type,
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify({
            "success": True,
            "map_focus": {
                "lat": coords["lat"],
                "lon": coords["lon"],
                "zoom": zoom,
                "location_name": coords["name"],
            },
            "infrastructure": infrastructure_data,
            "action_type": action_type,
            "visual_elements": {
                "highlight_area": True,
                "show_infrastructure": True,
                "show_real_time_data": True,
            },
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ai/map_focus_status")
def ai_map_focus_status():
    """Get AI map focus updates for frontend polling."""
    try:
        if ai_map_focus_data:
            return jsonify({"has_update": True, "focus_data": ai_map_focus_data})
        return jsonify({"has_update": False, "focus_data": None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
