import datetime
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
from django.http import HttpResponse
from django.shortcuts import render
from influxdb_client import InfluxDBClient

from .config import Config
from .forms import DatetimePicker


def index(request):
    return render(request, 'index.html')


def electricity_config(request):
    return render(request, 'electricity/config.html', context={'table': Config().electricity()})


def electricity_energy(request):
    plot = ''

    if request.method == 'POST':
        form = DatetimePicker(request.POST, choices=Config().electricity_name_choices())
        if form.is_valid():
            ts_from = datetime.datetime.combine(form.cleaned_data['from_date'], form.cleaned_data['from_time'])
            ts_to = datetime.datetime.combine(form.cleaned_data['to_date'], form.cleaned_data['to_time'])

            query = f"""
                    counterByTime = (table =<-, every) =>
                      table
                        |> window(every: every, createEmpty: true)
                        |> increase()
                        |> last()
                        |> duplicate(as: "_time", column: "_start")
                        |> window(every: inf)

                    from(bucket: "inosatiot_resources_sim")
                      |> range(start: {ts_from.isoformat()}+03:00, stop: {ts_to.isoformat()}+03:00)
                      |> filter(fn: (r) => r["_measurement"] == "{form.cleaned_data['name']}")
                      |> filter(fn: (r) => r["_field"] == "ep_imp")
                      |> counterByTime(every: {form.cleaned_data['aggregate_window']})
                      |> yield()"""

            client = InfluxDBClient(url="http://localhost:8086",
                                    token="KKIIV60BcG5u8BYRcPMc3EaZLcvKj73FWg0i3DXkmWUQ5enQtotEVK0VNbiNgTCGQL1bz5z-mOLXoaV_Puv5XQ==",
                                    org="Inosat"
                                    )

            df = client.query_api().query_data_frame(query)

            if 'plot' in request.POST:
                df = df.drop(columns=['result', 'table', '_field', '_measurement', '_start', '_stop'])
                df = df.set_index('_time')

                plot = go.Figure(
                    data=go.Scatter(
                        x=df.index,
                        y=df['_value'],
                        line=dict(
                            shape='vh'
                        )
                    ),
                    layout=go.Layout(
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                ).to_html(full_html=False, default_height=700)

            elif 'table' in request.POST:
                df = df.drop(columns=['result', 'table', '_field', '_measurement', '_start', '_stop'])
                df = df.set_index('_time')

                plot = df.to_html(classes=['table'])

            elif 'excel' in request.POST:
                df = df.drop(columns=['result', 'table', '_measurement', ])
                df['_value'] = pd.to_numeric(df['_value'])

                df_excel = df

                df_excel['_time'] = df_excel['_time'].dt.tz_localize(None)
                df_excel['_start'] = df_excel['_start'].dt.tz_convert('Europe/Minsk')
                df_excel['_start'] = df_excel['_start'].dt.tz_localize(None)
                df_excel['_stop'] = df_excel['_stop'].dt.tz_convert('Europe/Minsk')
                df_excel['_stop'] = df_excel['_stop'].dt.tz_localize(None)

                with BytesIO() as b:
                    # Use the StringIO object as the filehandle.
                    writer = pd.ExcelWriter(b, engine='xlsxwriter')
                    df.to_excel(writer,
                                sheet_name='Sheet1',
                                columns=['_time', '_value'],
                                header=['Нагрузка', 'Потребление'],
                                index=False,
                                startrow=4)

                    worksheet = writer.sheets['Sheet1']

                    worksheet.write(0, 0, 'Потребление электроэнергии')
                    worksheet.write(1, 0, 'от')
                    worksheet.write(1, 1, f"{df_excel.iloc[0, df_excel.columns.get_loc('_start')]:%Y-%m-%d %H:%M}")
                    worksheet.write(2, 0, 'до')
                    worksheet.write(2, 1, f"{df_excel.iloc[0, df_excel.columns.get_loc('_stop')]:%Y-%m-%d %H:%M}")

                    writer.save()
                    # Set up the Http response.
                    filename = 'energy.xlsx'
                    response = HttpResponse(
                        b.getvalue(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response

    else:
        ts_to = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        ts_to = ts_to.replace(second=0)

        ts_from = ts_to + datetime.timedelta(days=-1)

        form = DatetimePicker(initial={
            'from_time': ts_from,
            'from_date': ts_from,
            'to_time': ts_to,
            'to_date': ts_to,
        }, choices=Config().electricity_name_choices()
        )

    return render(request, 'electricity/energy.html',
                  context={
                      'plot': plot,
                      'form': form,
                  })
