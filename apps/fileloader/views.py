from django.shortcuts import redirect, render
import lib.GPX_analysis_step_complete as gpxreader


# Create your views here.
def loadfile(request):
    if request.method == 'POST':
        gpxfile = request.FILES['gpxfile']
        df_repeated = gpxreader.readgpx(gpxfile)
        df_json = df_repeated.to_json(orient='records')
        request.session['df_json'] = df_json
        return redirect('gpxreader')
    return render(request, 'fileloader.html')
