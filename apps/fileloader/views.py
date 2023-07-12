from django.shortcuts import redirect, render
import lib.GPX_analysis_step_complete as gpxreader


# Create your views here.
def loadfile(request):
    if request.method == 'POST':
        gpxfile = request.FILES['gpxfile']
        df, isLoaded = gpxreader.readgpx(gpxfile)
        if isLoaded:
            df_json = df.to_json(orient='records')
            request.session['df_json'] = df_json
            return redirect('gpxreader')
        else:
            return render(request, 'fileloader.html', {'error': 'File not loaded, please check the file format'})
    return render(request, 'fileloader.html')
