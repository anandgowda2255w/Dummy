FUNCTION_SCHEMAS = [
    {
        "name": "calculate_oee",
        "description": "Calculate OEE (Overall Equipment Effectiveness) for a specific machine. Returns availability, performance, quality, and OEE %.",
        "parameters": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "string", "description": "Machine ID e.g. M001"},
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end_date":   {"type": "string", "description": "End date YYYY-MM-DD"}
            },
            "required": ["machine_id", "start_date", "end_date"]
        }
    },
    {
        "name": "get_downtime_analytics",
        "description": "Get downtime analytics for ALL machines (plant-wide) within a date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date":   {"type": "string"}
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "get_machine_downtime",
        "description": "Get detailed downtime for a SPECIFIC machine including breakdown by reason.",
        "parameters": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date":   {"type": "string"}
            },
            "required": ["machine_id", "start_date", "end_date"]
        }
    },
    {
        "name": "get_rejection_analytics",
        "description": "Get rejection analytics for ALL machines (plant-wide) within a date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date":   {"type": "string"}
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "get_machine_rejection",
        "description": "Get detailed rejection data for a SPECIFIC machine with daily breakdown.",
        "parameters": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date":   {"type": "string"}
            },
            "required": ["machine_id", "start_date", "end_date"]
        }
    },
    {
        "name": "compare_machine_analytics",
        "description": "Compare two machines side-by-side on production, downtime, rejection, and OEE.",
        "parameters": {
            "type": "object",
            "properties": {
                "machine1":   {"type": "string"},
                "machine2":   {"type": "string"},
                "start_date": {"type": "string"},
                "end_date":   {"type": "string"}
            },
            "required": ["machine1", "machine2", "start_date", "end_date"]
        }
    },
    {
        "name": "get_production_summary",
        "description": "Get production summary for ALL machines (plant-wide) for a date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date":   {"type": "string"}
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "get_plant_production_summary",
        "description": "Alias for get_production_summary — plant-wide production summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date":   {"type": "string"}
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "get_machine_production_summary",
        "description": "Get detailed production summary for a SPECIFIC machine with daily breakdown.",
        "parameters": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date":   {"type": "string"}
            },
            "required": ["machine_id", "start_date", "end_date"]
        }
    },
    {
        "name": "get_maintenance_recommendation",
        "description": "Get maintenance recommendations based on downtime, alerts, and rejection patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date":   {"type": "string"}
            },
            "required": ["start_date", "end_date"]
        }
    }
]
