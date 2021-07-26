import datetime
import re
from io import BytesIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytz
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import render
from influxdb_client import InfluxDBClient
from plotly.graph_objects import layout

from .config import Config
from .forms import DatetimePicker


def global_view(request):
    theme = request.session.get('theme', 'dark')

    if 'theme' in request.POST:
        if theme == 'white':
            theme = 'dark'
        else:
            theme = 'white'

    request.session['theme'] = theme


def query_data(config: Config,
               ts_from: datetime.datetime,
               ts_to: datetime.datetime,
               measurement: str,
               aggregate_window: str):
    query = f"""
        counterByTime = (table =<-, every) =>
          table
            |> window(every: every, createEmpty: true)
            |> increase()
            |> last()
            |> duplicate(as: "_time", column: "_start")
            |> window(every: inf)

        from(bucket: "{config.influxdb()['bucket']}")
          |> range(start: {ts_from.isoformat()}, stop: {ts_to.isoformat()})
          |> filter(fn: (r) => r["_measurement"] == "{measurement}")
          |> filter(fn: (r) => r["_field"] == "ep_imp")
          |> counterByTime(every: {aggregate_window})
          |> yield()"""

    client = InfluxDBClient(
        url=config.influxdb()['url'],
        token=config.influxdb()['token'],
        org=config.influxdb()['org']
    )

    return client.query_api().query_data_frame(query)


def df_columns_to_scatter_data(df: pd.DataFrame):
    data = []
    for col in df.columns:
        data.append(
            go.Scatter(
                x=df.index,
                y=df[col],
                line=dict(
                    shape='vh'
                ),
                name=col
            )
        )
    return data


def df_apply_formula(row, formula1):
    try:
        return eval(formula1)
    except ZeroDivisionError:
        return np.NaN


def get_plotly_template(global_theme: str):
    if global_theme == 'white':
        return 'ggplot2'
    elif global_theme == 'dark':
        return 'plotly_dark'


def get_filename(label, ts_from, ts_to):
    filename = f"Электроэнергия _ {label} _ " \
               f"{ts_from.isoformat(sep=' ', timespec='minutes')} - " \
               f"{ts_to.isoformat(sep=' ', timespec='minutes')}"
    filename = filename.replace(':', '-')
    return filename


def output_plot_show(df, title, plotly_template):
    plot = go.Figure(
        data=df_columns_to_scatter_data(df),
        layout=go.Layout(
            legend=dict(
                yanchor="top",
                y=-0.1,
                xanchor="left",
                x=0
            ),
            template=plotly_template,
            title=title,
            yaxis=layout.YAxis(
                title="кВтч"
            ),
        )
    ).to_html(
        full_html=False,
        config={'displayModeBar': True, 'displaylogo': False, 'showTips': False}
    )

    plot = '<div class="h-100 pb-4">' + plot[5:]

    return plot


def output_plot_png(df, title, filename):
    plot = go.Figure(
        data=df_columns_to_scatter_data(df),
        layout=go.Layout(
            legend=dict(
                yanchor="top",
                y=-0.1,
                xanchor="left",
                x=0
            ),
            template='plotly_white',
            title=title,
            yaxis=layout.YAxis(
                title="кВтч"
            )
        ),
    ).to_image(format='png', width=1200, height=800)

    response = FileResponse(
        BytesIO(plot),
        as_attachment=True,
        content_type="image/png",
        filename=filename)

    return response


def output_table_show(df):
    df.index = df.index.strftime('%Y-%m-%d %H:%M')

    stat_min = df.min(numeric_only=True)
    stat_mean = df.mean(numeric_only=True)
    stat_max = df.max(numeric_only=True)
    stat_sum = df.sum(numeric_only=True)

    df.loc["Минимум"] = stat_min
    df.loc["Среднее"] = stat_mean
    df.loc["Максимум"] = stat_max
    df.loc["Сумма"] = stat_sum

    plot = df.to_html(
        classes=['table', 'table-hover', ],
        justify='left',
        float_format='{:.1f}'.format
    )

    return plot


def output_table_excel(df, filename, ts_from, ts_to):
    df.index = df.index.tz_localize(None)

    stat_min = df.min(numeric_only=True)
    stat_mean = df.mean(numeric_only=True)
    stat_max = df.max(numeric_only=True)
    stat_sum = df.sum(numeric_only=True)

    df.loc["Минимум"] = stat_min
    df.loc["Среднее"] = stat_mean
    df.loc["Максимум"] = stat_max
    df.loc["Сумма"] = stat_sum

    buffer = BytesIO()
    writer = pd.ExcelWriter(buffer, engine='xlsxwriter')

    df.to_excel(
        writer,
        index=True,
        sheet_name='Sheet1',
        startrow=4
    )
    worksheet = writer.sheets['Sheet1']

    worksheet.write(0, 0, 'Потребление электроэнергии')
    worksheet.write(1, 0, 'от')
    worksheet.write(1, 1, ts_from.isoformat(sep=' ', timespec='minutes'))
    worksheet.write(2, 0, 'до')
    worksheet.write(2, 1, ts_to.isoformat(sep=' ', timespec='minutes'))

    writer.save()
    buffer.seek(0)

    response = FileResponse(
        buffer,
        as_attachment=True,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=filename + '.xlsx')

    return response


def index(request):
    global_view(request)

    return render(request, 'index.html')


def electricity_config(request):
    global_view(request)
    return render(
        request,
        'electricity/config.html',
        context={
            'table_e': Config().e,
            'table_eg': Config().eg
        })


def electricity_energy(request):
    global_view(request)

    plot = ''

    if request.method == 'POST':
        form = DatetimePicker(request.POST, choices=Config().electricity_label_choices())
        if form.is_valid():
            config = Config()

            # контруируем время от и до
            tzinfo = pytz.timezone(settings.TIME_ZONE)
            ts_from = datetime.datetime.combine(form.cleaned_data['from_date'],
                                                form.cleaned_data['from_time'])
            ts_to = datetime.datetime.combine(form.cleaned_data['to_date'],
                                              form.cleaned_data['to_time'])
            ts_from = tzinfo.localize(ts_from)
            ts_to = tzinfo.localize(ts_to)

            tag = form.cleaned_data['tag']

            if tag in config.e:
                df = query_data(
                    config=config,
                    ts_from=ts_from,
                    ts_to=ts_to,
                    measurement=config.e[tag].influxdb_meas,
                    aggregate_window=form.cleaned_data['aggregate_window'])

                df['_value'] = pd.to_numeric(df['_value'])

                # переименовываем стобцы
                df = df.rename(columns={'_value': config.e[tag].label})

                df = df.set_index('_time')
                df.index = df.index.tz_convert(settings.TIME_ZONE)
                df.index = df.index.rename('Время')

                df = df.drop(columns=['result', 'table', '_field', '_measurement', '_start', '_stop'])

                # имя файла для экспорта
                filename = get_filename(config.e[tag].label, ts_from, ts_to)

                if 'plot_show' in request.POST:
                    plot = output_plot_show(df, config.e[tag].label, get_plotly_template(request.session['theme']))

                elif 'plot_png' in request.POST:
                    return output_plot_png(df, config.e[tag].label, filename + ".png")

                elif 'table_show' in request.POST:
                    plot = output_table_show(df)

                elif 'table_excel' in request.POST:
                    return output_table_excel(df, filename, ts_from, ts_to)

            elif tag in config.eg:
                # определяем, какие теги используются в формуле
                formula = config.eg[tag].formula
                formula_tr = formula.translate({ord(c): ' ' for c in "()+-/*"}).strip()
                tags = set(re.split(' +', formula_tr))

                for t in tags:
                    formula = formula.replace(t, f"row['{t}']")

                # запрашиваем отдельные столбцы
                df = {}
                for t in tags:
                    df[t] = query_data(
                        config=config,
                        ts_from=ts_from,
                        ts_to=ts_to,
                        measurement=config.e[t].influxdb_meas,
                        aggregate_window=form.cleaned_data['aggregate_window'])
                    df[t] = df[t].drop(columns=['result', 'table', '_field', '_measurement', '_start', '_stop'])
                    df[t] = df[t].rename(columns={'_value': t})

                # объединяем столбцы в один датафрейм
                df_total = None
                for key in df:
                    if df_total is None:
                        df_total = df[key]
                    else:
                        df_total = df_total.merge(on='_time', right=df[key], how='outer')

                df_total = df_total.fillna(0)
                df_total[config.eg[tag].label] = df_total.apply(df_apply_formula, args=(formula,), axis=1)
                df_total = df_total.sort_index(axis=0)

                # переименовываем стобцы
                for t in tags:
                    if t in df_total.columns:
                        df_total = df_total.rename(columns={t: config.e[t].label})

                df_total = df_total.set_index('_time')
                df_total.index = df_total.index.tz_convert(settings.TIME_ZONE)
                df_total.index = df_total.index.rename('Время')

                # имя файла для экспорта
                filename = get_filename(config.eg[tag].label, ts_from, ts_to)

                if 'plot_show' in request.POST:
                    plot = output_plot_show(df_total, config.eg[tag].label,
                                            get_plotly_template(request.session['theme']))

                elif 'plot_png' in request.POST:
                    return output_plot_png(df_total, config.eg[tag].label, filename + ".png")

                elif 'table_show' in request.POST:
                    plot = output_table_show(df_total)

                elif 'table_excel' in request.POST:
                    return output_table_excel(df_total, filename, ts_from, ts_to)

    else:
        ts_to = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        ts_to = ts_to.replace(second=0)

        ts_from = ts_to + datetime.timedelta(days=-1)

        form = DatetimePicker(initial={
            'from_time': ts_from,
            'from_date': ts_from.strftime('%Y-%m-%d'),
            'to_time': ts_to,
            'to_date': ts_to.strftime('%Y-%m-%d'),
        }, choices=Config().electricity_label_choices()
        )

    return render(
        request, 'electricity/energy.html',
        context={
            'plot': plot,
            'form': form,
        })
