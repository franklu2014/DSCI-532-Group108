import pandas as pd
import altair as alt
import geopandas as gpd
import json
from shapely.geometry import Point, Polygon
import shapely.wkt
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import numpy as np

app = dash.Dash(__name__, assets_folder='assets')
app.config['suppress_callback_exceptions'] = True
server = app.server

app.title = 'Vancouver Crime Stats'

df = pd.read_csv('../data/crimedata_csv_all_years.csv')
df = df.query('NEIGHBOURHOOD == NEIGHBOURHOOD & NEIGHBOURHOOD != "Musqueam" & NEIGHBOURHOOD != "Stanley Park"')

list_of_locations = df['NEIGHBOURHOOD'].dropna().unique()
list_of_locations = np.insert(list_of_locations, 0, 'ALL')
list_of_crimes = df['TYPE'].unique()
list_of_crimes = np.insert(list_of_crimes, 0, 'ALL')
list_of_years = ['YEAR', 'MONTH', 'DAY', 'HOUR']

def plot_by_neighbor(year_init = 2010, year_end = 2018, neighbourhood="ALL", crime = "ALL", time_scale = "YEAR"):
    
    df_line = df.query('@year_init <= YEAR & YEAR <= @year_end')
    
    if neighbourhood != "ALL":
        if crime != "ALL":
            df_line = df_line.query('TYPE == @crime & NEIGHBOURHOOD == @neighbourhood').groupby([time_scale]).count().reset_index()
        else:    
            df_line = df_line.query('NEIGHBOURHOOD == @neighbourhood').groupby([time_scale]).count().reset_index()
    else:
        neighbourhood = 'All Neighbourhoods'
        if crime != "ALL":
            df_line = df_line.query('TYPE == @crime').groupby([time_scale]).count().reset_index()
        else:
            crime = 'All Crimes'
            df_line = df_line.groupby([time_scale]).count().reset_index() 
    
    chart = alt.Chart(df_line).mark_line().encode(
        alt.X(time_scale+':N'),
        alt.Y('TYPE:Q', title='Number of Crimes'),
        alt.Color(value="blue")
    ).configure_axisX(
        labelAngle=90,
        grid=True
    ).configure(
        background='#f7e0bc' #HEX color code
    ).properties(
    height=300,
    width=500,
    title= neighbourhood + ': ' + crime
    )
    return chart

geojson_filepath = '../data/our_geojson.geojson'

def open_geojson(path):
    """
    Opens a geojson file at "path" filepath
    """
    with open(path) as json_data:
        d = json.load(json_data)
    return d

def get_geopandas_df(path):
    """
    Creates geopandas dataframe from geeojson file 
    at "path" filepath
    """
    open_json = open_geojson(path)
    gdf = gpd.GeoDataFrame.from_features((open_json))
    return gdf

gdf = get_geopandas_df(geojson_filepath)
gdf = gdf.rename(columns = {'Name': 'NEIGHBOURHOOD'}).drop(columns = 'description')

def plot_choropleth(year_init = 2010, year_end = 2018, crime_type = 'all'):

    crime_cnt = (df.query('@year_init <= YEAR & YEAR <= @year_end').groupby(['NEIGHBOURHOOD', 'TYPE'])[['MINUTE']]
                .count().rename(columns = {'MINUTE': 'COUNT'})
                .reset_index())

    if(crime_type.lower() == 'all'):
        crime_type = 'All Crimes'
        crime_cnt = crime_cnt.groupby('NEIGHBOURHOOD')[['COUNT']].sum().reset_index()
    else:
        crime_cnt = crime_cnt.query('TYPE == @crime_type').groupby('NEIGHBOURHOOD')[['COUNT']].sum().reset_index()

    crime_geo_cnt = gdf.merge(crime_cnt, on = 'NEIGHBOURHOOD')

    alt_json = json.loads(crime_geo_cnt.to_json())
    alt_base = alt.Data(values = alt_json['features'])

    base_map = alt.Chart(alt_base, 
                        title = f"Vancouver: {crime_type}").mark_geoshape(
            stroke='white',
            strokeWidth=1
        ).encode(
            tooltip = [alt.Tooltip('properties.NEIGHBOURHOOD:N', title =  'Neighbourhood'), 
                alt.Tooltip('properties.COUNT:Q', title = 'Count')]
        ).properties(
            width=1000,
            height=600
        )

    choro = alt.Chart(alt_base).mark_geoshape(
        fill = 'lightgray', 
        stroke = 'white'
    ).encode(
        color = alt.Color('properties.COUNT:Q', legend = alt.Legend(title = 'Crime Count'))
    )

    return (choro + base_map).properties(width = 700, height = 400)


app.layout = html.Div([

    html.Div([
        #Header
        html.Img(src='https://img.icons8.com/wired/64/000000/policeman-male.png', style={'float':'left'}),
        html.H1('Vancouver Crime Stats', style={'float':'left', 'margin-left':'10px'}),
    ],style={'position':'absolute'}),
    
    html.Div([
        # Drop Down Menus

        html.H3('Crime Type'),
        dcc.Dropdown(
        id='crime-chart',
        options=[
            {'label': i, 'value': i}
            for i in list_of_crimes
        ],
        value = 'ALL',
        placeholder = 'ALL',
        style=dict(width='90%',
            verticalAlign="middle"
            )
        ),

        html.H3('Years to Include'),
        html.Div([
            dcc.RangeSlider(
                id='year-slider',
                min=df['YEAR'].min(),
                max=df['YEAR'].max(),
                step=1,
                marks={i:'{}'.format(i) for i in range(df['YEAR'].min(),df['YEAR'].max(),2)},
                value=[df['YEAR'].min(), df['YEAR'].max()]
            ),
        ], style={'width': '90%', 'margin-left':'20px'}),
        html.Br(),

        html.H3('Neighbourhood'),
        dcc.Dropdown(
        id='dd-chart',
        options=[
            {'label': i, 'value': i}
            for i in list_of_locations
        ],
        value = 'ALL',
        placeholder = 'ALL',
        style=dict(width='90%',
            verticalAlign="middle"
            )
        ),

        html.H3('Time Scale'),
        dcc.Dropdown(
        id='year-chart',
        options=[
            {'label': i, 'value': i}
            for i in list_of_years
        ],
        value = 'YEAR',
        style=dict(width='90%',
            verticalAlign="middle"
            )
        ),


    ], style={'float': 'left', 'width': '30%', 'height':'800px', 'margin-top': '100px', 'background-color':'#f7bb86'}),
    
    html.Div([
        # Graphs
        html.Div([
            dcc.Slider(
                id='slider-updatemode',
        marks={'0.1': '0.1', '1': '1'},
        max=1,
        min=0.1,
        value=1,
        step=0.01,
        updatemode='drag',
        vertical=True
            ),
        ], style={'height': '100px', 'margin-left':'900px'}),
        html.Br(),
        
        html.Iframe(
            # Crime Map
            sandbox='allow-scripts',
            id = 'choropleth',
            height='400',
            width='100%',
            style={'border-width': '0'},
            
                srcDoc=plot_choropleth().to_html()
            ),
        
        html.Iframe(
            # Crime Trends
            sandbox='allow-scripts',
            id='plot',
            height='400',
            width='100%',
            style={'border-width': '0'},

            srcDoc=plot_by_neighbor().to_html()
        
            ),
    ], style={'float': 'right', 'width': '70%', 'margin-top': '100px'}),        
], style={})

@app.callback(
    dash.dependencies.Output('plot', 'srcDoc'),
    [dash.dependencies.Input('year-slider', 'value'), dash.dependencies.Input('dd-chart', 'value'), dash.dependencies.Input('crime-chart', 'value'), dash.dependencies.Input('year-chart', 'value')])
def update_plot(year_range, location, types, year):

    updated_plot = plot_by_neighbor(year_init=year_range[0], year_end=year_range[1], neighbourhood=location, crime=types, time_scale=year).to_html()

    return updated_plot

@app.callback(
    dash.dependencies.Output('choropleth', 'srcDoc'),
    [dash.dependencies.Input('year-slider', 'value'), dash.dependencies.Input('crime-chart', 'value')])
def update_choropleth(year_range, type):

    updated_plot = plot_choropleth(year_init=year_range[0], year_end=year_range[1], crime_type=type).to_html()

    return updated_plot

if __name__ == '__main__':
    app.run_server(debug=True)