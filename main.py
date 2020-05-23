"""New York Covid-19 Data Explorer

This script generates a standalone HTML file that allows
the user to quickly visualize a large amount of data on a 
county level.

This script requires that `bokeh` be installed within the Python
environment you are running this script in.

This script also requires `template.html` to be located in the 
same directory as the script 
"""

from bokeh.models import ColumnDataSource, CustomJS, Slider, RadioButtonGroup, Div, Button, TableColumn, DateFormatter, DataTable, LinearColorMapper, DateSlider
from bokeh.io import show, curdoc
from bokeh.events import ButtonClick
from bokeh.layouts import row, column, layout
from bokeh.palettes import RdYlBu11 as palette
from bokeh.plotting import figure, output_file
from bokeh.sampledata.us_counties import data as counties
from bokeh.themes import built_in_themes
import json, urllib.request, sys, os.path
from os.path import join, dirname
from os import path
from datetime import date


def download_data():
    """Downloads Covid-19 data from the NY Health Department's website in JSON format

    Returns:
        data: the JSON data in a list
    """
    if path.exists('xdss-u53e.json'):
        pass
    else:
        urllib.request.urlretrieve('https://health.data.ny.gov/resource/xdss-u53e.json', 'xdss-u53e.json')
    with open('xdss-u53e.json') as json_file:
        data = json.load(json_file)
    return data

def parse_data(source_data, data_start_date, data_end_date):
    """Parses the previously downloaded data based on the provided fields

    Args:
        source_data: the JSON data that was downloaded
        data_start_date: the first date given in the data
        data_end_date: the last date given in the data

    Returns:
        source: a subset of data that is stored/displayed in the plot
        dates_source: the full dataset placed into a ColumnDataSource
    """
    global counties
    county_xs = [county["lons"] for county in counties.values() if county["state"] == "ny"]
    county_ys = [county["lats"] for county in counties.values() if county["state"] == "ny"]
    county_names = [county['name'] for county in counties.values() if county["state"] == "ny"]
    
    county_new_positives = [county['new_positives'] for county in source_data if county['test_date'] == data_end_date]
    county_cumulative_number_of_positives = [county['cumulative_number_of_positives'] for county in source_data if county['test_date'] == data_end_date]
    county_total_number_of_tests = [county['total_number_of_tests'] for county in source_data if county['test_date'] == data_end_date]
    county_cumulative_number_of_tests = [county['cumulative_number_of_tests'] for county in source_data if county['test_date'] == data_end_date]
    total_data = {}
    for county in source_data:
        date = county['test_date'].split("T")[0]
        if date not in total_data:
            total_data[date] = [[], [], [], []]
        total_data[date][0].append(county['new_positives'])
        total_data[date][1].append(county['cumulative_number_of_positives'])
        total_data[date][2].append(county['total_number_of_tests'])
        total_data[date][3].append(county['cumulative_number_of_tests'])
    data=dict(x=county_xs,
              y=county_ys,
              name=county_names,
              new_positives=county_new_positives,
              cumulative_number_of_positives=county_cumulative_number_of_positives,
              total_number_of_tests=county_total_number_of_tests,
              cumulative_number_of_tests=county_cumulative_number_of_tests)
    source = ColumnDataSource(data=data )
    dates_source = ColumnDataSource(data=total_data)
    return source, dates_source

def init_plot(data):
    """Initializes the plots

    Args:
        data: data for the current day that is displayed by the plots initially

    Returns:
        p: plot that is graphed
        patches: reference to the patches for the plot (handle coloring)
        color_mapper: reference to the colors/maps that are used in the plot
    """
    global palette
    palette = tuple(palette)
    color_mapper = LinearColorMapper(palette=palette)
    TOOLS = "wheel_zoom,reset,hover,save"

    p = figure(plot_width=1000, plot_height=800, sizing_mode="stretch_width",
               title="New York Covid-19 Data", tools=TOOLS,
               x_axis_location=None, y_axis_location=None,
               tooltips=[("Name", "@name"), ("New Positives", "@new_positives"), ("Cumulative Number of Positives", "@cumulative_number_of_positives"), ("Total Number of Tests", "@total_number_of_tests"), ("Cumulative Number of Tests", "@cumulative_number_of_tests"),])
    p.grid.grid_line_color = None
    p.hover.point_policy = "follow_mouse"
    patches = p.patches('x', 'y', source=data,
               fill_color={'field': 'new_positives', 'transform': color_mapper},
               fill_alpha=0.7, line_color="white", line_width=0.5)
    return p, patches, color_mapper

def init_widgets(data_start_date, data_end_date, source):
    """Initializes the widgets to be displayed adjacent the plot

    Args:
        data_start_date: the first date given in the data
        data_end_date: the last date given in the data
        source: data for the current day that is displayed by the widgets initially

    """
    date_slider = DateSlider(title="Date Range: ", start=date.fromisoformat(data_start_date.split("T")[0]), end=date.fromisoformat(data_end_date.split("T")[0]), value=date.fromisoformat(data_end_date.split("T")[0]), step=86400000, sizing_mode="stretch_width")
    radio_button_group = RadioButtonGroup(labels=["New Positives", "Cumulative Number of Positives", "Total Number of Tests", "Cumulative Number of Tests"], active=0, sizing_mode="stretch_width")
    button = Button(label="Play", button_type="primary")
    columns = [
            TableColumn(field="name", title="County"),
            TableColumn(field="new_positives", title="New Positives"),
    ]
    data_table = DataTable(source=source, columns=columns, sizing_mode="stretch_both", index_position=None)
    return date_slider, radio_button_group, button, data_table

def init_widgets_callbacks(source, dates_source, date_slider, radio_button_group, button, data_table, p, patches, color_mapper):
    """(Huge messy function that) Creates the callbacks for the widgets

    Args:
        source: a subset of data that is stored/displayed in the plot
        dates_source: the full dataset placed into a ColumnDataSource
        date_slider: allows the user to change dates in the plot
        radio_button_group: allows the user to change the parameter to be plotted
        button: cycles through all the dates available
        data_table: a table that provides data based on the given date/parameter
        p: plot that is graphed
        patches: reference to the patches for the plot (handle coloring)
        color_mapper: reference to the colors/maps that are used in the plot
    """
    callback = CustomJS(args=dict(source=source, dates_source=dates_source, date_slider=date_slider, radio_button_group=radio_button_group, data_table=data_table, patches = patches, p=p, cmap=color_mapper), code="""

    var labels = ["new_positives", "cumulative_number_of_positives", "total_number_of_tests", "cumulative_number_of_tests"];
    var current_parameter_index = radio_button_group.active;
    var current_parameter_label = labels[current_parameter_index];
    var current_date = date_slider.value;
    current_date = new Date(current_date).toLocaleDateString('en-CA', { timeZone: 'Atlantic/Reykjavik' });
    var update_new_positives = dates_source.data[current_date][0];
    var update_cumulative_number_of_positives = dates_source.data[current_date][1];
    var update_total_number_of_tests = dates_source.data[current_date][2];
    var update_cumulative_number_of_tests = dates_source.data[current_date][3];

    source.data['new_positives'] = update_new_positives;
    source.data['cumulative_number_of_positives'] = update_cumulative_number_of_positives;
    source.data['total_number_of_tests'] = update_total_number_of_tests;
    source.data['cumulative_number_of_tests'] = update_cumulative_number_of_tests;

    patches.data_source.data['new_positives'] = update_new_positives;
    patches.data_source.data['cumulative_number_of_positives'] = update_cumulative_number_of_positives;
    patches.data_source.data['total_number_of_tests'] = update_total_number_of_tests;
    patches.data_source.data['cumulative_number_of_tests'] = update_cumulative_number_of_tests;
    
    // Patches need to be manually updated and cycled due to a bug in Bokeh :/
    var other_index = (current_parameter_index + 1) % 3
    patches.glyph.fill_color = {field: labels[other_index], transform:cmap};
    patches.glyph.fill_color = {field: current_parameter_label, transform:cmap};
    
    var human_labels = ["New Positives", "Cumulative Number of Positives", "Total Number of Tests", "Cumulative Number of Tests"]
    data_table.columns.pop();
    const TableColumn = Bokeh.Models('TableColumn');
    data_table.columns.push(new TableColumn({title: human_labels[current_parameter_index],
                                             field: current_parameter_label}));
    data_table.change.emit();
    """)

    button_callback = CustomJS(args=dict(date_slider=date_slider), code="""
    if (date_slider.value === date_slider.end){
        date_slider.value = date_slider.start;
    }
    var playing = setInterval(function(){ 
        if  (date_slider.value < date_slider.end){
            console.log("hi");
            date_slider.value += 86400000;
        }    
        else{
            clearInterval(playing);
        }
    }, 1000);
    """)
    date_slider.js_on_change('value', callback)
    radio_button_group.js_on_change('active', callback)
    button.js_on_event(ButtonClick, button_callback)

def main():
    """Handles the main program flow"""
    global layout
    desc = Div(text=open(join(dirname(__file__), "template.html")).read(), sizing_mode="stretch_width")
    source_data = download_data()
    # The website only provides 8 (out of 62) values for the start date so let's grab the second to first date
    data_start_date, data_end_date = source_data[-10]['test_date'], source_data[0]['test_date']
    source, dates_source = parse_data(source_data, data_start_date, data_end_date)
    data = source.data
    p, patches, color_mapper = init_plot(data)
    date_slider, radio_button_group, button, data_table = init_widgets(data_start_date, data_end_date, source)
    init_widgets_callbacks(source, dates_source, date_slider, radio_button_group, button, data_table, p, patches, color_mapper)    
    inputs = column(radio_button_group, date_slider, button, data_table)
    layout = layout([
    [desc],
    [p, inputs],
    ])
    output_file("final.html", title="New York Covid-19 Data")
    show(layout)

if __name__ == "__main__":
    main()