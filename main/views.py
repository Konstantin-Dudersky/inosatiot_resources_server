import datetime

from django.shortcuts import render
from influxdb_client import InfluxDBClient

from .config import Config
from .forms import DatetimePicker


def index(request):
    return render(request, 'index.html')


def electric(request):
    return render(request, 'electricity/index.html')


def electricity_config(request):
    return render(request, 'electricity/config.html', context={'table': Config().electricity()})


def electricity_per_3_min(request):
    fig = ''
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
                      |> range(start: -10h)
                      |> filter(fn: (r) => r["_measurement"] == "{form.cleaned_data['name']}")
                      |> filter(fn: (r) => r["_field"] == "ep_imp")
                      |> counterByTime(every: 3m)
                      |> yield()"""

            client = InfluxDBClient(url="http://localhost:8086",
                                    token="KKIIV60BcG5u8BYRcPMc3EaZLcvKj73FWg0i3DXkmWUQ5enQtotEVK0VNbiNgTCGQL1bz5z-mOLXoaV_Puv5XQ==",
                                    org="Inosat"
                                    )

            df = client.query_api().query_data_frame(query)

            df = df.drop(columns=['result', 'table', '_field', '_measurement', '_start', '_stop'])
            df = df.set_index('_time')
            # print(df)
            # df.info()

            import plotly.express as px
            fig = px.line(data_frame=df,
                          line_shape='hv',
                          template='plotly_white',
                          ).to_html(full_html=False, default_height=700)
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

    # print(Config.electricity_name_choices_st())

    return render(request, 'electricity/per_3_min.html',
                  context={
                      'plot_div': fig,
                      'form': form
                  })
