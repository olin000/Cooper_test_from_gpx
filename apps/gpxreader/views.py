from django.shortcuts import redirect, render
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import io
import base64
import lib.GPX_analysis_step_complete as gpxreader

# Create your views here.


def readgpx(request):
    if request.method == 'POST':
        gpxfile = request.FILES['gpxfile']
        gpxfile = request.FILES['gpxfile']
        df, isLoaded = gpxreader.readgpx(gpxfile)
        if isLoaded:
            df_json = df.to_json(orient='records')
            request.session['df_json'] = df_json
            return redirect('gpxreader')
        else:
            return render(request, 'fileloader.html', {'error': 'File not loaded, please check the file format'})
    if 'df_json' in request.session:
        df_json = request.session['df_json']
        df = pd.read_json(df_json, orient='records')
        df['offset_distance_cumsum'] = df.iloc[:, 2].shift(720).fillna(0)
        df['cooper_test'] = 0
        mask = df['time_cumsum'] > 720
        df.loc[mask, 'cooper_test'] = df['distance_cumsum'] - df['offset_distance_cumsum']
        df['cumulative_max'] = df['cooper_test'].cummax()
        # df.to_csv('output.csv', sep=',', index=False, header=False)

        x = np.arange(len(df) - 720)
        y1 = np.array(df['cooper_test'])[720:]
        y2 = np.array(df['cumulative_max'])[720:]

        max_value = df['cooper_test'].max()
        max_axis = df['cooper_test'].max() + 50
        min_value = df['cooper_test'].replace(0, np.nan).min()
        min_axis = max(min_value - 50, 0)

        # Create bar trace
        bar_trace = go.Bar(x=x, y=y1, marker=dict(color='steelblue'), name='Trials')

        # Create line trace
        line_trace = go.Scatter(x=x, y=y2, mode='lines', line=dict(color='red'), name='Maximum')

        # Create layout
        layout = go.Layout(xaxis=dict(title='Trials'), yaxis=dict(title='Cooper test distance (m)',
                                                                  range=[min_axis, max_axis]),
                           legend=dict(x=0.4, y=1.2, traceorder='normal'), bargap=0, bargroupgap=0)

        # Add text annotation
        index = np.where(df['cooper_test'] == max_value)[0][0] - 720
        if index >= 0:
            text_annotation = go.layout.Annotation(x=x[index] + 0.1, y=y2[-1] + 12,
                                                   text=np.round(max_value,
                                                                 decimals=1), showarrow=False, font=dict(color='blue'))
            layout.annotations = [text_annotation]

        # Create figure
        fig = go.Figure(data=[bar_trace, line_trace], layout=layout)
        # fig.update_traces(marker_color='blue', marker_line_color='blue', selector=dict(type="bar"))
        fig.update_traces(marker_line_width=0)

        chart = fig.to_html()

        return render(request, 'chart.html', {
            'chart': chart,
        })
    else:
        return render(request, 'fileloader.html')