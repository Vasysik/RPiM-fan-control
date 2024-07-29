from flask import Blueprint, render_template, request, jsonify
import json
import os
from datetime import datetime, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))
fan_control = Blueprint('fan_control', __name__,
                        template_folder='templates',
                        static_folder='static',
                        static_url_path='static')

def read_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def write_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

config = read_json(os.path.join(current_dir, 'config.json'))
settings = read_json(os.path.join(current_dir, 'settings.json'))

from influxdb_client import InfluxDBClient, QueryApi
client = InfluxDBClient(url=read_json(config['influxdb_config_path'])['influxdb_url'], 
                        token=read_json(config['influxdb_config_path'])['influxdb_token'])
query_api = client.query_api()

@fan_control.route('/')
def index():
    influxdb_bucket = config['influxdb_bucket']
    influxdb_org = config['influxdb_org']
    
    query = f'from(bucket: "{influxdb_bucket}") |> range(start: -5m) |> filter(fn: (r) => r._measurement == "fan_status") |> last()'
    result = query_api.query(org=influxdb_org, query=query)
    return render_template('fan_control.html')

@fan_control.route('/api/current', methods=['GET'])
def api_current():
    influxdb_bucket = config['influxdb_bucket']
    influxdb_org = config['influxdb_org']

    query = f'from(bucket: "{influxdb_bucket}") |> range(start: -5m) |> filter(fn: (r) => r._measurement == "fan_status") |> last()'
    result = query_api.query(org=influxdb_org, query=query)
    current_data = {}
    if result:
        for table in result:
            record = table.records[0]
            field_name = record.get_field()
            if field_name == 'temperature':
                current_data["temperature"] = record.get_value()
            elif field_name == 'fan_state':
                current_data["fan_state"] = record.get_value()
            elif field_name == 'rpm':
                current_data["rpm"] = record.get_value()
    return jsonify(current_data)

@fan_control.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'GET':
        global settings
        settings = read_json(os.path.join(current_dir, 'settings.json'))
        return jsonify(settings)
    elif request.method == 'POST':
        data = request.json
        write_json(os.path.join(current_dir, 'settings.json'), data)
        return jsonify({"status": "success"}), 200

@fan_control.route('/api/graph_data')
def get_graph_data():
    graph_type = request.args.get('type', 'temperature')
    time_range = int(request.args.get('range', 60))  # Default to 1 minute

    # Определяем интервал агрегации в зависимости от временного диапазона
    if time_range <= 300:  # 5 минут или меньше
        interval = '1s'
    elif time_range <= 1800:  # 30 минут или меньше
        interval = '5s'
    elif time_range <= 3600:  # 1 час или меньше
        interval = '10s'
    elif time_range <= 21600:  # 6 часов или меньше
        interval = '30s'
    elif time_range <= 43200:  # 12 часов или меньше
        interval = '1m'
    else:
        interval = '5m'

    query = f"""
    from(bucket:"{config['influxdb_bucket']}")
    |> range(start: -{time_range}s)
    |> filter(fn: (r) => r._measurement == "fan_status")
    |> filter(fn: (r) => r._field == "{graph_type}" or r._field == "fan_state")
    |> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)
    |> yield(name: "mean")
    """

    result = client.query_api().query(query, org=config['influxdb_org'])

    timestamps = []
    values = []
    fan_states = []

    for table in result:
        for record in table.records:
            timestamps.append(record.get_time().strftime('%Y-%m-%d %H:%M:%S'))
            if record.get_field() == graph_type:
                values.append(record.get_value())
            elif record.get_field() == 'fan_state':
                fan_states.append(round(record.get_value()))  # Округляем состояние вентилятора

    return jsonify({
        'timestamps': timestamps,
        graph_type: values,
        'fan_state': fan_states
    })