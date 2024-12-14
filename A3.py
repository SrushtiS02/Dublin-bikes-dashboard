import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# Fetch real-time data from the API
api_key = "4e9943c44828c97fac47e8c723130cf98d370008"
url = f"https://api.jcdecaux.com/vls/v1/stations?contract=Dublin&apiKey={api_key}"
response = requests.get(url)

if response.status_code == 200:
    stations_data = response.json()
    df = pd.json_normalize(stations_data)
else:
    raise Exception(f"Failed to fetch data: HTTP {response.status_code}")

# Clean and preprocess data
df.rename(columns={
    'number': 'station_number',
    'name': 'station_name',
    'address': 'station_address',
    'bike_stands': 'total_capacity',
    'available_bike_stands': 'empty_stands',
    'available_bikes': 'bikes_available',
    'position.lat': 'latitude',
    'position.lng': 'longitude',
    'last_update': 'timestamp'
}, inplace=True)
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df['total_bike_stands'] = df['bikes_available'] + df['empty_stands']
df['utilization_rate'] = (df['bikes_available'] / df['total_bike_stands']) * 100

# Summary Statistics
total_bikes = df['bikes_available'].sum()
total_stands = df['empty_stands'].sum()
last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Initialize the Dash app
app = dash.Dash(__name__)

# Layout the dashboard
app.layout = html.Div([
    html.H1("Dublin Bikes Dashboard", style={'textAlign': 'center', 'padding': '10px'}),

    # Display Summary Statistics
    html.Div([
        html.H3(f"Total Bikes Available: {total_bikes}"),
        html.H3(f"Total Stands Available: {total_stands}"),
        html.H4(f"Last Updated: {last_updated}")
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),

    # Dropdown for Station Selection
    html.Div([
        html.Label("Select a Station:"),
        dcc.Dropdown(
            id='station_dropdown',
            options=[
                {'label': name, 'value': name} for name in df['station_name'].unique()
            ],
            placeholder="Select a station to highlight...",
            style={'width': '50%', 'margin': '0 auto'}
        )
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),

    # Visualizations
    html.Div([
        html.Div([
            dcc.Graph(id='map_figure')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

        html.Div([
            dcc.Graph(id='bar_chart')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    ], style={'marginBottom': '20px'}),

    html.Div([
        html.Div([
            dcc.Graph(
                figure=px.scatter_mapbox(
                    df,
                    lat="latitude",
                    lon="longitude",
                    size="bikes_available",
                    color="status",
                    hover_name="station_name",
                    animation_frame="timestamp",
                    title="Bike Availability Over Time",
                    zoom=12,
                    height=400
                ).update_layout(mapbox_style="carto-positron")
            )
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

        html.Div([
            dcc.Graph(
                figure=px.pie(
                    df,
                    names="station_name",
                    values="utilization_rate",
                    title="Station Capacity Utilization",
                    height=400
                )
            )
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    ])
])

# Callback to update map based on dropdown selection
@app.callback(
    Output('map_figure', 'figure'),
    [Input('station_dropdown', 'value')]
)
def update_map(selected_station):
    filtered_df = df.copy()
    if selected_station:
        filtered_df = filtered_df[filtered_df['station_name'] == selected_station]

    fig_map = px.scatter_mapbox(
        filtered_df,
        lat="latitude",
        lon="longitude",
        size="bikes_available",
        color="status",
        hover_name="station_name",
        hover_data={"station_address": True, "bikes_available": True, "empty_stands": True},
        title="Dublin Bikes Station Map",
        zoom=12,
        height=400
    )
    fig_map.update_layout(mapbox_style="open-street-map")
    return fig_map

# Callback to update bar chart based on dropdown selection
@app.callback(
    Output('bar_chart', 'figure'),
    [Input('station_dropdown', 'value')]
)
def update_bar_chart(selected_station):
    filtered_df = df.copy()
    if selected_station:
        filtered_df = filtered_df[filtered_df['station_name'] == selected_station]

    fig_bar = px.bar(
        filtered_df,
        x="station_name",
        y="bikes_available",
        color="status",
        title="Bike Availability for Selected Station",
        height=400
    )
    fig_bar.update_layout(xaxis_tickangle=-45)
    return fig_bar

# Run the app on a new port
if __name__ == '__main__':
    app.run_server(debug=True, port=8051)
