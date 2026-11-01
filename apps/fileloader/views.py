import logging
from django.shortcuts import redirect, render
import lib.GPX_analysis_step_complete as gpx_analyzer

logger = logging.getLogger('db')


def loadfile(request):
    if request.method == 'POST':
        gpxfile = request.FILES.get('gpxfile')
        if not gpxfile:
            return render(request, 'fileloader.html', {
                'error': 'No file selected. Please choose a .gpx file to upload.'
            })

        if not gpxfile.name.lower().endswith('.gpx'):
            return render(request, 'fileloader.html', {
                'error': 'Invalid file format. Only .gpx files are supported.'
            })

        result, error_msg = gpx_analyzer.calculate_cooper_test(gpxfile)
        if error_msg:
            return render(request, 'fileloader.html', {'error': error_msg})

        request.session['chart_result'] = result
        logger.info(f"Successfully processed GPX file: {gpxfile.name}")
        return redirect('gpxreader')

    return render(request, 'fileloader.html')
