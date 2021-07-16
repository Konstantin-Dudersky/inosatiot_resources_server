import plotly.express as px
import yaml
from django.shortcuts import render
from influxdb_client import InfluxDBClient
from plotly.offline import plot
import plotly.graph_objects as go


def index(request):
    config = ""
    with open('config.yaml') as stream:
        config = yaml.safe_load(stream)

    return render(request, 'index.html')


def electric(request):
    return render(request, 'electricity/index.html')


def electricity_config(request):
    config = ""
    with open('config.yaml') as stream:
        config = yaml.safe_load(stream)
    table = config['electricity']
    return render(request, 'electricity/config.html', context={'table': table})


def electricity_per_3_min(request):
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
      |> filter(fn: (r) => r["_measurement"] == "counter1")
      |> filter(fn: (r) => r["_field"] == "epimp")
      |> counterByTime(every: 3m)
      |> yield()"""

    client = InfluxDBClient(url="http://localhost:8086",
                            token="KKIIV60BcG5u8BYRcPMc3EaZLcvKj73FWg0i3DXkmWUQ5enQtotEVK0VNbiNgTCGQL1bz5z-mOLXoaV_Puv5XQ==",
                            org="Inosat"
                            )

    df = client.query_api().query_data_frame(query)

    df = df.drop(columns=['result', 'table', '_field', '_measurement', '_start', '_stop'])
    df = df.set_index('_time')
    print(df)
    df.info()



    import plotly.express as px
    fig = px.scatter(data_frame=df)



    # Generating some data for plots.
    x = [i for i in range(-10, 11)]
    y1 = [3*i for i in x]
    y2 = [i**2 for i in x]
    y3 = [10*abs(i) for i in x]

    # List of graph objects for figure.
    # Each object will contain on series of data.
    graphs = []

    # Adding linear plot of y1 vs. x.
    graphs.append(
        go.Scatter(x=x, y=y1, mode='lines', name='Line y1')
    )

    # Adding scatter plot of y2 vs. x.
    # Size of markers defined by y2 value.
    graphs.append(
        go.Scatter(x=x, y=y2, mode='markers', opacity=0.8,
                   marker_size=y2, name='Scatter y2')
    )

    # Adding bar plot of y3 vs x.
    graphs.append(
        go.Bar(x=x, y=y3, name='Bar y3')
    )

    # Setting layout of the figure.
    layout = {
        'title': 'Title of the figure',
        'xaxis_title': 'X',
        'yaxis_title': 'Y',
        'height': 420,
        'width': 560,
    }

    # Getting HTML needed to render the plot.
    plot_div = plot({'data': graphs, 'layout': layout},
                    output_type='div')

    return render(request, 'electricity/per_3_min.html', context={'plot_div': fig.to_html(full_html=False, default_height=700)})
