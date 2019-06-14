import pandas as pd

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

acc = pd.read_csv('accidents2017.csv', index_col = 0).dropna(how='any', axis = 0)
veh = pd.read_csv('vehicles2017.csv', index_col = 0).dropna(how='any', axis = 0)

MAPBOX = 'abc'
SEVERITY_LOOKUP = {'Fatal' : 'red',
                    'Serious' : 'orange',
                    'Slight' : 'yellow'}
SEX_LOOKUP = {'Female' : 'yellow',
              'Male' : 'blue'}
SLIGHT_FRAC = 0.1
SERIOUS_FRAC = 0.5
DAYSORT = dict(zip(['Friday', 'Monday', 'Saturday','Sunday', 'Thursday', 'Tuesday', 'Wednesday'],
                  [4, 0, 5, 6, 3, 1, 2]))

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(children='UK Traffic Accidents'),

    html.Div([
        dcc.Checklist( # Checklist for the three different severity values
            options=[
                {'label': sev, 'value': sev} for sev in acc['Accident_Severity'].unique()
            ],
            values=[sev for sev in acc['Accident_Severity'].unique()],
            labelStyle={
                'display': 'inline-block',
                'paddingRight' : 10,
                'paddingLeft' : 10,
                'paddingBottom' : 5,
                },
            id="severityChecklist",   
		),

    	dcc.Checklist( # Checklist for the dats of week, sorted using the sorting dict created earlier
            options=[
                {'label': day[:3], 'value': day} for day in sorted(acc['Day_of_Week'].unique(), key=lambda k: DAYSORT[k])
            ],
            values=[day for day in acc['Day_of_Week'].unique()],
            labelStyle={  # Different padding for the checklist elements
                'display': 'inline-block',
                'paddingRight' : 10,
                'paddingLeft' : 10,
                'paddingBottom' : 5,
                },
            id="dayChecklist",
		),

		html.Div([  # Holds the map & the widgets
            dcc.Graph(id="map") # Holds the map in a div to apply styling to it  
        ],
        style={}),

		html.Div([  # Holds the barchart
	            dcc.Graph(id="bar")
	            #style={'height' : '50%'})
	        ],
	        style={
	            "width" : '100%', 
	            'display' : 'inline-block', 
	            'boxSizing' : 'border-box'
	    })
    ])
])


@app.callback(
    Output(component_id='bar', component_property='figure'),
    [Input(component_id='severityChecklist', component_property='values'),
    Input(component_id='dayChecklist', component_property='values'),
    ]
)
def updateBarChart(severity, weekdays):
    # The rangeslider is selects inclusively, but a python list stops before the last number in a range
    
    # Create a copy of the dataframe by filtering according to the values passed in.
    # Important to create a copy rather than affect the global object.
    acc2 = pd.DataFrame(acc[[
        'Accident_Severity','Speed_limit','Number_of_Casualties']][
            (acc['Accident_Severity'].isin(severity)) & 
            (acc['Day_of_Week'].isin(weekdays))
            ].groupby(['Accident_Severity','Speed_limit']).sum()).reset_index()

    # Create the field for the hovertext. Doing this after grouping, rather than
    #  immediately after loading the df. Should be quicker this way.
    def barText(row):
        return 'Speed Limit: {}mph<br>{:,} {} accidents'.format(row['Speed_limit'],
                                                                row['Number_of_Casualties'],
                                                                row['Accident_Severity'].lower())
    acc2['text'] = acc2.apply(barText, axis=1)

    # One trace for each accidents severity
    traces = []
    for sev in severity:
        traces.append({
            'type' : 'bar',
            'y' : acc2['Number_of_Casualties'][acc2['Accident_Severity'] == sev],
            'x' : acc2['Speed_limit'][acc2['Accident_Severity'] == sev],
            'text' : acc2['text'][acc2['Accident_Severity'] == sev],
            'hoverinfo' : 'text',
            'marker' : {
                'color' : SEVERITY_LOOKUP[sev], # Use the colur lookup for consistency
            'line' : {'width' : 2,
                      'color' : '#333'}},
            'name' : sev,
        })  
        
    fig = {'data' : traces,
          'layout' : {}
          }

    # Returns the figure into the 'figure' component property, update the bar chart
    return fig

@app.callback(
    Output(component_id='map', component_property='figure'),
    [Input(component_id='severityChecklist', component_property='values'),
    Input(component_id='dayChecklist', component_property='values'),
    ]
)
def updateMapBox(severity, weekdays):
    # List of hours again
    # Filter the dataframe
    acc2 = acc[
            (acc['Accident_Severity'].isin(severity)) &
            (acc['Day_of_Week'].isin(weekdays))
            ]

    # Once trace for each severity value
    traces = []
    for sev in sorted(severity, reverse=True):
        # Set the downsample fraction depending on the severity
        sample = 1
        if sev == 'Slight':
            sample = SLIGHT_FRAC
        elif sev == 'Serious':
            sample = SERIOUS_FRAC
        # Downsample the dataframe and filter to the current value of severity
        acc3 = acc2[acc2['Accident_Severity'] == sev].sample(frac=sample)
            
        # Scattermapbox trace for each severity
        traces.append({
            'type' : 'scattermapbox',
            'mode' : 'markers',
            'lat' : acc3['Latitude'],
            'lon' : acc3['Longitude'],
            'marker' : {
                'color' : SEVERITY_LOOKUP[sev], # Keep the colour consistent
                'size' : 2,
            },
            'hoverinfo' : 'text',
            'name' : sev,
            'legendgroup' : sev,
            'showlegend' : False,
            'text' : acc3['Local_Authority_(District)'] # Text will show location
        })
        
        # Append a separate marker trace to show bigger markers for the legend. 
        #  The ones we're plotting on the map are too small to be of use in the legend.
        traces.append({
            'type' : 'scattermapbox',
            'mode' : 'markers',
            'lat' : [0],
            'lon' : [0],
            'marker' : {
                'color' : SEVERITY_LOOKUP[sev],
                'size' : 10,
            },
            'name' : sev,
            'legendgroup' : sev,
            
        })
    layout = {}
    fig = dict(data=traces, layout=layout)
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)