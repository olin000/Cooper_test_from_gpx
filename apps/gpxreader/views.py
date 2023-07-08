from django.shortcuts import render
import pandas as pd

# Create your views here.


def readgpx(request):
    df_json = request.session['df_json']
    df_repeated = pd.read_json(df_json, orient='records')
    df_repeated.to_csv('output.csv', sep=',', index=False, header=False)
    return render(request, 'gpxreader.html', {
        'nazwa': "nazwa",
    })
