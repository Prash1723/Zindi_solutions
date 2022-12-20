import json
from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, Legend, LogColorMapper, GeoJSONDataSource, LinearColorMapper, ColorBar, Range1d, NumeralTickFormatter, HoverTool, LabelSet, Panel, Tabs
from bokeh.models.widgets import TableColumn, DataTable, NumberFormatter, Dropdown, Select, RangeSlider
from bokeh.palettes import Category20c, Spectral, GnBu, brewer, PRGn, RdYlGn
from bokeh.io import curdoc, output_notebook, show, output_file
from bokeh.layouts import row, column, gridplot
from bokeh.palettes import Viridis6 as palette
from bokeh.transform import cumsum

import geopandas as gpd
import pycountry
import pycountry_convert as pc

import pandas as pd
import numpy as np
import math

# Load Data
df = pd.read_csv(r'data/clean_train.csv')

borders = 'mapping/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp'
gdf = gpd.read_file(borders)[['ADMIN', 'ADM0_A3', 'geometry']]

# Rename columns
gdf.columns = ['country', 'country_code', 'geometry']

## Map
# Initiate Map Chart
d1 = round(df.groupby(['country'])['total_cost'].apply(lambda x: pd.Series({
            'total_revenue': x.sum(), 
            'avg_revenue': x.mean(),
            'tours' : len(x)
        }))).unstack().reset_index()

def findcountry(country_name):
    """Find the official country name"""
    try:
        return pycountry.countries.get(name=country_name).official_name
    except:
        return country_name

def findcontinent(country_name):
    """Find the official continent name the country is situated in"""
    try:
        co_alpha2 = pc.country_name_to_country_alpha2(country_name)
        co_cont_code = pc.country_alpha2_to_continent_code(co_alpha2)
        co_cont_name = pc.convert_continent_code_to_continent_name(co_cont_code)
        return co_cont_name
    except:
        return not_found

# Assign official names to data
d1['country'] = d1['country'].apply(findcountry)

gdf['country'] = gdf['country'].apply(findcountry)

# Correct names
co_dict = {
        "Korea, Republic of": "South Korea",
        "Russian Federation": "Russia",
        "Swaziland": "Kingdom of Eswatini"
        }

islands = [
        "Republic of Mauritius", 
        "Bermuda",
        "Cape Verde",
        "Republic of Malta",
        "Commonwealth of Dominica",
        "Republic of Singapore",
        "Union of the Comoros"
        ]

# Correct name of the country
d1['country'] = d1['country'].apply(lambda x: co_dict.get(x,x))

# Assign continent name to origin country
d1['continent'] = d1['country'].apply(findcontinent)

# Merge data with co-ordinates
geo_df = gdf.merge(d1, left_on='country', right_on='country', how='left')

# Treat null values
geo_df['continent'].fillna('not present', inplace=True)

for i in ['total_revenue', 'avg_revenue', 'tours']:
    geo_df[i].fillna(0, inplace=True)

# Read data to json
df_json = json.loads(geo_df.to_json())

# Convert to string like object
map_data = json.dumps(df_json)

# Assign Source
map_source = GeoJSONDataSource(geojson = map_data)

# Map Geometry
color_mapper = LinearColorMapper(palette=palette[::-1],
        low=d1['avg_revenue'].min(), high=d1['avg_revenue'].max())

# Colour scale
tick_labels = {
        '2': 'Index 2',
        '3': 'Index 3',
        '4':'Index 4',
        '5':'Index 5',
        '6':'Index 6',
        '7':'Index 7',
        '8':'Index 8'
        }

color_bar = ColorBar(color_mapper=color_mapper, label_standoff=5, width = 600, height = 30,
    border_line_color=None,location = (20,0), orientation = 'horizontal',
    major_label_overrides = tick_labels)

# Map
TOOLS = "pan,wheel_zoom,reset,hover,save"

map_all = figure(plot_width=725, plot_height=500, title="Revenue(Average) from different countries", 
        tools=TOOLS, x_axis_location=None, y_axis_location=None, 
        tooltips = [
            ("Country", "@country"),
            ("Total Revenue", "$@total_revenue{0,0.0}"),
            ("Revenue per tour", "$@avg_revenue{0,0.0}"),
            ("Tourist visits", "@tours")
            ])

map_all.grid.grid_line_color = None
map_all.hover.point_policy = "follow_mouse"

map_all.patches("xs", "ys", source=map_source, fill_color={"field":"total_revenue", "transform":color_mapper},
        fill_alpha=0.7, line_color="black", line_width=0.5)

map_all.add_layout(color_bar, 'below')

tab1 = Panel(child=map_all, title="Map")

## Tours vs Revenue by origin country
map_sc = ColumnDataSource(d1)

# ~ select
menu = [("Africa", "Africa"),
        ("North America", "North America"),
        ("South America", "South America"), 
        ("Europe", "Europe"), 
        ("Asia", "Asia"),
        ("Oceania", "Oceania")]

cont_sel = Select(title="Select Continent", value="Africa", options=["Africa", "North America", "South America", "Asia", "Europe", "Oceania"])

co_sc = figure(plot_width=725, plot_height=400, title="Revenue(Total) from different countries",
        x_axis_label="Number of Tours", y_axis_label="Revenue", tools=TOOLS,
        tooltips = [
            ("Country", "@country"),
            ("Total Revenue", "$@total_revenue{0,0.0}"),
            ("Revenue per tour", "$@avg_revenue{0,0.0}"),
            ("Tourist visits", "@tours")
            ])

# - Function
def up_scat(attr, old, new):
    """Select continent name"""
    name = cont_sel.value
    map_sc.data = d1.query('continent=="'+name+'"')

co_sc.grid.grid_line_color = None
co_sc.hover.point_policy = "follow_mouse"

co_sc.circle(x='tours', y='total_revenue', size=10, source=map_sc, fill_color={"field":"total_revenue", "transform":color_mapper},
        fill_alpha=0.7, line_color="black", line_width=0.5)

cont_sel.on_change('value', up_scat)

co2n = gridplot([[cont_sel], [co_sc]])

# = Tabs
tab2 = Panel(child=co2n, title="Scatter plot")

co_tabs = Tabs(tabs=[tab1,tab2])

## Islands
df_isl = d1.query('country in @islands')

isl_source = ColumnDataSource(df_isl)

i_fig = figure(plot_width=375, plot_height=200, title="Revenue from small island countries",
        y_range=isl_source.data['country'], y_axis_label="Isles", x_axis_location=None,
        tooltips = [
            ("Country", "@country"),
            ("Total revenue", "$@total_revenue{0,0.0}"),
            ("Revenue per tour", "$@avg_revenue{0,0.0}"),
            ("Tourist visits", "@tours")
            ])

i_fig.xgrid.grid_line_color = None

i_fig.hbar(y="country", left="total_revenue", source=isl_source.data, right=0, height=0.5, fill_color="#b3de69")

i_tab = Panel(child=i_fig, title="Islands")

## Age group

age_df = df.groupby('age_group').agg({
        'total_cost': ["sum", "mean", "count"],
        'total_male': "sum",
        'total_female': "sum"
    }).reset_index()

age_df.columns = ['age_group', 'total_revenue', 'avg_revenue', 'total_tours', 'male_tourists', 'female_tourists']

age_df['percentage_rev'] = round(age_df['total_revenue'] * 100 / age_df['total_revenue'].sum())

age_df['angles'] = age_df['total_revenue'] / age_df['total_revenue'].sum() * 2*math.pi

age_df['colors'] = Category20c[age_df['age_group'].nunique()]

s1 = ColumnDataSource(age_df)

age_pi = figure(plot_width=250, plot_height=200, title="Revenue from different age group",
        x_range=s1.data['age_group'], x_axis_location=None, y_axis_location=None,
        tooltips=[
            ('Group', "@age_group"),
            ('Revenue', "$@total_revenue{0,0.0}"),
            ('%', "@percentage_rev%"),
            ('Male', "@male_tourists"),
            ('Female', "@female_tourists")
            ])

age_pi.grid.grid_line_color = None

age_pi.wedge(x=len(age_df['age_group'])/2, y=0, radius=1.5, source=s1,
        start_angle=cumsum('angles', include_zero=True),
        end_angle=cumsum('angles'),
        line_color="white",
        fill_color='colors')

pie_tab1 = Panel(child=age_pi, title="Age")

## Source of Information

info_df = df.groupby('info_source').agg({
        'total_cost': ["sum", "mean", "count"],
        'total_male': "sum",
        'total_female': "sum"
    }).reset_index()

info_df.columns = ['info_source', 'total_revenue', 'avg_revenue', 'total_tours', 'male_tourists', 'female_tourists']

info_df['percentage_rev'] = round(info_df['total_revenue'] * 100 / info_df['total_revenue'].sum())

info_df['angles'] = info_df['total_revenue'] / info_df['total_revenue'].sum() * 2*math.pi

info_df['colors'] = Category20c[info_df['info_source'].nunique()]

s2 = ColumnDataSource(info_df)

info_pi = figure(plot_width=250, plot_height=200, title="Revenue by Information source",
        x_range=s2.data['info_source'], x_axis_location=None, y_axis_location=None,
        tooltips=[
            ('Source', "@info_source"),
            ('Revenue', "$@total_revenue{0,0.0}"),
            ('%', "@percentage_rev%"),
            ('Male', "@male_tourists"),
            ('Female', "@female_tourists")
            ])

info_pi.grid.grid_line_color = None

info_pi.wedge(x=len(info_df['info_source'])/2, y=0, radius=3, source=s2,
        start_angle=cumsum('angles', include_zero=True),
        end_angle=cumsum('angles'),
        line_color="white",
        fill_color='colors')

pie_tab2 = Panel(child=info_pi, title="info")

## Tour Activity

ma_df = df.groupby('main_activity').agg({
        'total_cost': ["sum", "mean", "count"],
        'total_male': "sum",
        'total_female': "sum"
    }).reset_index()

ma_df.columns = ['main_activity', 'total_revenue', 'avg_revenue', 'total_tours', 'male_tourists', 'female_tourists']

ma_df['percentage_rev'] = round(ma_df['total_revenue'] * 100 / ma_df['total_revenue'].sum())

ma_df['angles'] = ma_df['total_revenue'] / ma_df['total_revenue'].sum() * 2*math.pi

ma_df['colors'] = Category20c[ma_df['main_activity'].nunique()]

s3 = ColumnDataSource(ma_df)

ma_pi = figure(plot_width=250, plot_height=200, title="Revenue by tour activity",
        x_range=s3.data['main_activity'], x_axis_location=None, y_axis_location=None,
        tooltips=[
            ('Activity', "@main_activity"),
            ('Revenue', "$@total_revenue{0,0.0}"),
            ('%', "@percentage_rev%"),
            ('Male', "@male_tourists"),
            ('Female', "@female_tourists")
            ])

ma_pi.grid.grid_line_color = None

ma_pi.wedge(x=len(ma_df['main_activity'])/2, y=0, radius=3, source=s3,
        start_angle=cumsum('angles', include_zero=True),
        end_angle=cumsum('angles'),
        line_color="white",
        fill_color='colors')

pie_tab3 = Panel(child=ma_pi, title="activity")

## Source of Information

p_df = df.groupby('purpose').agg({
        'total_cost': ["sum", "mean", "count"],
        'total_male': "sum",
        'total_female': "sum"
    }).reset_index()

p_df.columns = ['purpose', 'total_revenue', 'avg_revenue', 'total_tours', 'male_tourists', 'female_tourists']

p_df['percentage_rev'] = round(p_df['total_revenue'] * 100 / p_df['total_revenue'].sum())

p_df['angles'] = p_df['total_revenue'] / p_df['total_revenue'].sum() * 2*math.pi

p_df['colors'] = Category20c[p_df['purpose'].nunique()]

s4 = ColumnDataSource(p_df)

p_pi = figure(plot_width=250, plot_height=200, title="Revenue by tour purpose",
        x_range=s4.data['purpose'], x_axis_location=None, y_axis_location=None,
        tooltips=[
            ('Purpose', "@purpose"),
            ('Revenue', "$@total_revenue{0,0.0}"),
            ('%', "@percentage_rev%"),
            ('Male', "@male_tourists"),
            ('Female', "@female_tourists")
            ])

p_pi.grid.grid_line_color = None

p_pi.wedge(x=len(p_df['purpose'])/2, y=0, radius=2.5, source=s4,
        start_angle=cumsum('angles', include_zero=True),
        end_angle=cumsum('angles'),
        line_color="white",
        fill_color='colors')

pie_tab4 = Panel(child=p_pi, title="purpose")

pie_tabs = Tabs(tabs=[pie_tab1, pie_tab2, pie_tab3, pie_tab4])

## Continents

cont_df = d1.groupby('continent').agg({
    'total_revenue': ["sum", "mean", "count"],
    'tours': "sum"
    }).reset_index()

cont_df.columns = ['continent', 'total_revenue', 'avg_revenue', 'countries', 'tours']

cont_df['percentage_rev'] = round(cont_df['total_revenue'] * 100 / cont_df['total_revenue'].sum())

sc = ColumnDataSource(cont_df)

cont_bar = figure(plot_width=379, plot_height=200, title="Revenue by continents",
        y_range=sc.data['continent'], y_axis_label='Continents', x_axis_location=None,
        tooltips=[
            ('Continent', "@continent"),
            ('Revenue', "$@total_revenue{0,0.0}"),
            ('%', "@percentage_rev%"),
            ('Avg. revenue', "@avg_revenue"),
            ('tours', "@tours")
            ])

cont_bar.xgrid.grid_line_color = None

cont_bar.hbar(y="continent", left="total_revenue", source=sc.data, right=0, height=0.5, fill_color="#b3de69")

cont_tab = Panel(child=cont_bar, title="Continents")

bar_tabs = Tabs(tabs=[cont_tab, i_tab])

# Ranking of countries

top_sc = ColumnDataSource(d1.sort_values(by='total_revenue', ascending=False).head(10))

bot_sc = ColumnDataSource(d1.sort_values(by='total_revenue', ascending=True).head(10))

co_cols = [
        TableColumn(field='country', title="Country"),
        TableColumn(field='total_revenue', title="Total Revenue", formatter=NumberFormatter(format='$0,0[.]00', text_align='right', language='it')),
        TableColumn(field='avg_revenue', title="Average Revenue", formatter=NumberFormatter(format='$0,0[.]00', text_align='right', language='it')),
        TableColumn(field='tours', title='Tours'),
        TableColumn(field='continent', title='Continent')
        ]

co_top = DataTable(source=top_sc, columns=co_cols)

co_bot = DataTable(source=bot_sc, columns=co_cols)

top_tab = Panel(child=co_top, title='Top 10 countries')

bot_tab = Panel(child=co_bot, title='Bottom 10 countries')

list_tabs = Tabs(tabs=[top_tab, bot_tab])

# Arrange the Dashboard
layout = column(row(co_tabs, column(row(bar_tabs, pie_tabs), list_tabs)))
curdoc().add_root(layout)
curdoc().title = "Tanzania Tourism Dashboard"
