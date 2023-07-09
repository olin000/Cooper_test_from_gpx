from django.shortcuts import redirect, render
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import io
import base64
import lib.GPX_analysis_step_complete as gpxreader

# Create your views here.


def readgpx(request):
    if request.method == 'POST':
        gpxfile = request.FILES['gpxfile']
        df = gpxreader.readgpx(gpxfile)
        df_json = df.to_json(orient='records')
        request.session['df_json'] = df_json
        return redirect('gpxreader')
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

    matplotlib.use('agg')
    fig, ax = plt.subplots()

    max_value = df['cooper_test'].max()
    max_axis = df['cooper_test'].max() + 50
    min_value = df['cooper_test'].replace(0, np.nan).min()
    min_axis = max(min_value - 50, 0)

    ax.bar(x, y1, alpha=1.0, width=1.0, color='steelblue')
    ax.set_ylim(min_axis, max_axis)
    ax.plot(x, y2, color='red', label='Maximum')

    ax.text(x[df.loc[df['cooper_test'] == max_value].index[0] - 720] + 0.1, y2[-1] + 3, np.round(max_value, decimals=1),
            color='blue')

    ax.set_xlabel('Trials')
    ax.set_ylabel('Cooper test distance (m)')

    ax.legend(loc='lower left').get_frame().set_alpha(1.0)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    base64_plot = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render(request, 'gpxreader.html', {
        'base64_plot': base64_plot,
    })
