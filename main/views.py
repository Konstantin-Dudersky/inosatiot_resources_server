import datetime
import re
import sys
from io import BytesIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import pytz
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import render
from influxdb_client import InfluxDBClient
from loguru import logger

from .config import Config
from .forms import DatetimePicker

logger.remove()
logger.add(sys.stderr, level='DEBUG')
logger.add('logs/log.txt', level='INFO', rotation='5 MB')


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
               field: str,
               aggwindow: str,
               aggfunc: str,
               ) -> pd.DataFrame:
    # fields
    fields = [f.strip() for f in field.split(',')]

    field_str = f'|> filter(fn: (r) => r["_field"] == "{fields[0]}"'
    for i in range(1, len(fields)):
        field_str += f' or r["_field"] == "{fields[i]}"'
    field_str += ")"
    logger.trace(field_str)

    # aggfuncs
    aggfuncs = [f.strip() for f in aggfunc.split(',')]

    aggfunc_str = f'|> filter(fn: (r) => r["aggfunc"] == "{aggfuncs[0]}"'
    for i in range(1, len(aggfuncs)):
        aggfunc_str += f' or r["aggfunc"] == "{aggfuncs[i]}"'
    aggfunc_str += ")"
    logger.trace(aggfunc_str)

    # |> filter(fn: (r) => r["_field"] == "{field}")
    # |> filter(fn: (r) => r["aggfunc"] == "{aggfunc}")
    query = f"""
        from(bucket: "{config.influxdb()['bucket']}")
          |> range(start: {ts_from.isoformat()}, stop: {ts_to.isoformat()})
          |> filter(fn: (r) => r["_measurement"] == "{measurement}")
          {field_str}
          |> filter(fn: (r) => r["aggwindow"] == "{aggwindow}")
          {aggfunc_str}
          |> yield()"""

    logger.trace(f"flux query: {query}")

    client = InfluxDBClient(
        url=config.influxdb()['url'],
        token=config.influxdb()['token'],
        org=config.influxdb()['org'],
    )

    return client.query_api().query_data_frame(query)


def df_columns_to_scatter_data(df: pd.DataFrame, data_line_shape: str = 'linear'):
    data = []

    # если графиков несколько, запоминаем имя последнего столбца
    # чтобы не включать его в группу stackgroup
    last_col = '' if len(df.columns) == 1 else df.columns[-1]

    for col in df.columns:
        stackgroup = '' if col == last_col else 'stackgroup'

        data.append(
            go.Scatter(
                x=df.index,
                y=df[col],
                line=go.scatter.Line(
                    shape=data_line_shape,
                ),
                name=col,
                stackgroup=stackgroup,
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
        return 'seaborn'
    elif global_theme == 'dark':
        return 'plotly_dark'


def get_filename(label, ts_from, ts_to):
    filename = f"Электроэнергия _ {label} _ " \
               f"{ts_from.isoformat(sep=' ', timespec='minutes')} - " \
               f"{ts_to.isoformat(sep=' ', timespec='minutes')}"
    filename = filename.replace(':', '-')
    return filename


# def output_plot_show(df: pd.DataFrame,
#                      data_line_shape: str,
#                      layout_title: str,
#                      layout_yaxis_title: str,
#                      plotly_template: str):
#     plot = go.Figure(
#         data=df_columns_to_scatter_data(df, data_line_shape=data_line_shape),
#         layout=go.Layout(
#             legend=dict(
#                 yanchor="top",
#                 y=-0.1,
#                 xanchor="left",
#                 x=0
#             ),
#             template=plotly_template,
#             title=layout_title,
#             yaxis=go.layout.YAxis(
#                 title=layout_yaxis_title
#             ),
#         )
#     ).to_html(
#         full_html=False,
#         config={'displayModeBar': True, 'displaylogo': False, 'showTips': False}
#     )
#
#     plot = '<div class="h-100 pb-4">' + plot[5:]
#
#     return plot


def plot_stacked_scatter(
        df: pd.DataFrame,
        data_line_shape: str,
        layout_template: str,
        layout_title: str,
        layout_yaxis_title: str,
) -> go.Figure:
    return go.Figure(
        data=df_columns_to_scatter_data(df, data_line_shape=data_line_shape),
        layout=go.Layout(
            legend=dict(
                yanchor="top",
                y=-0.1,
                xanchor="left",
                x=0
            ),
            template=layout_template,
            title=layout_title,
            yaxis=go.layout.YAxis(
                title=layout_yaxis_title
            )
        ),
    )


def output_plot_show(fig: go.Figure):
    html = fig.to_html(
        full_html=False,
        config={'displayModeBar': True, 'displaylogo': False, 'showTips': False}
    )

    html = '<div class="h-100 pb-4">' + html[5:]

    return html


def output_plot_png(fig: go.Figure, filename: str):
    image = fig.to_image(format='png', width=1200, height=800)

    return FileResponse(
        BytesIO(image),
        as_attachment=True,
        content_type="image/png",
        filename=filename)


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


def output_table_excel(df: pd.DataFrame, filename: str, header: str):
    df.index = df.index.tz_localize(None)

    ts_from = df.index.min().to_pydatetime()
    ts_to = df.index.max().to_pydatetime()

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

    worksheet.write(0, 0, header)
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


def info(request):
    global_view(request)

    return render(request, 'info.html')


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
        form = DatetimePicker(
            request.POST,
            choices_tag=Config().electricity_label_choices(),
            choices_field=[
                ['ep_imp', 'Активная энергия (+)'],
                ['eq_imp', 'Реактивная энергия (+)'],
                ['ep_exp', 'Активная энергия (-)'],
                ['eq_exp', 'Реактивная энергия (-)'],
            ],
        )

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

            if ts_from >= ts_to:
                return alert_timerange(form, request, "Потребление ЭЭ")

            tag = form.cleaned_data['tag']

            logger.debug(f"try to load tag: {tag}, from: {ts_from}, to: {ts_to},"
                         f"aggwindow: {form.cleaned_data['aggregate_window']}")

            if tag in config.e:
                df = query_data(
                    config=config,
                    ts_from=ts_from,
                    ts_to=ts_to,
                    measurement=config.e[tag].influxdb_meas,
                    field=form.cleaned_data['field'],
                    aggwindow=form.cleaned_data['aggregate_window'],
                    aggfunc='sum',
                )

                if len(df) == 0:
                    return alert_nodata(form, request, "Потребление ЭЭ")

                df['_value'] = pd.to_numeric(df['_value'])

                # переименовываем стобцы
                df = df.rename(columns={'_value': config.e[tag].label})

                df = df.set_index('_time')
                df = df.sort_index(axis=0)
                df.index = df.index.tz_convert(settings.TIME_ZONE)
                df.index = df.index.rename('Время')

                df = df.drop(columns=['result', 'table', '_field', '_measurement', '_start', '_stop',
                                      'aggfunc', 'aggwindow', 'datatype'])

                # имя файла для экспорта
                filename = get_filename(config.e[tag].label, ts_from, ts_to)

                if 'plot_show' in request.POST:
                    fig = plot_stacked_scatter(
                        df=df,
                        data_line_shape='vh',
                        layout_template=get_plotly_template(request.session['theme']),
                        layout_title=config.e[tag].label,
                        layout_yaxis_title="Потребленная ЭЭ, кВт*ч",
                    )

                    plot = output_plot_show(fig)

                elif 'plot_png' in request.POST:
                    fig = plot_stacked_scatter(
                        df=df,
                        data_line_shape='vh',
                        layout_template='seaborn',
                        layout_title=config.e[tag].label,
                        layout_yaxis_title="Потребленная ЭЭ, кВт*ч",
                    )
                    return output_plot_png(fig, filename + ".png")

                elif 'table_show' in request.POST:
                    plot = output_table_show(df)

                elif 'table_excel' in request.POST:
                    return output_table_excel(df, filename, "Потребленная ЭЭ")

            elif tag in config.eg:
                # определяем, какие теги используются в формуле
                formula = config.eg[tag].formula
                tags = set(re.split(' +', formula.translate({ord(c): ' ' for c in "()+-/*"}).strip()))

                # заменим теги в формуле: tag -> row['tag']
                formula_for_apply = ''
                for t in re.split(' +', formula.translate({ord(c): f' {c} ' for c in "()+-/*"}).strip()):
                    if len(t) > 2:
                        formula_for_apply += f"row['{t}']"
                    else:
                        formula_for_apply += t

                # запрашиваем отдельные столбцы
                df = {}
                for t in tags:
                    df[t] = query_data(
                        config=config,
                        ts_from=ts_from,
                        ts_to=ts_to,
                        measurement=config.e[t].influxdb_meas,
                        field=form.cleaned_data['field'],
                        aggwindow=form.cleaned_data['aggregate_window'],
                        aggfunc='sum',
                    )
                    df[t] = df[t].drop(columns=['result', 'table', '_field', '_measurement', '_start', '_stop',
                                                'aggfunc', 'aggwindow', 'datatype'])
                    df[t] = df[t].rename(columns={'_value': t})

                # объединяем столбцы в один датафрейм
                df_total = None
                for key in df:
                    if df_total is None:
                        df_total = df[key]
                    else:
                        df_total = df_total.merge(on='_time', right=df[key], how='outer')

                df_total = df_total.fillna(0)
                df_total[config.eg[tag].label] = df_total.apply(df_apply_formula, args=(formula_for_apply,), axis=1)

                # переименовываем стобцы
                for t in tags:
                    if t in df_total.columns:
                        df_total = df_total.rename(columns={t: config.e[t].label})

                df_total = df_total.set_index('_time')
                df_total = df_total.sort_index(axis=0)
                df_total.index = df_total.index.tz_convert(settings.TIME_ZONE)
                df_total.index = df_total.index.rename('Время')

                # имя файла для экспорта
                filename = get_filename(config.eg[tag].label, ts_from, ts_to)

                if 'plot_show' in request.POST:
                    fig = plot_stacked_scatter(
                        df=df_total,
                        data_line_shape='vh',
                        layout_template=get_plotly_template(request.session['theme']),
                        layout_title=config.eg[tag].label,
                        layout_yaxis_title="Потребленная ЭЭ, кВт*ч",
                    )

                    plot = output_plot_show(fig)

                elif 'plot_png' in request.POST:
                    fig = plot_stacked_scatter(
                        df=df_total,
                        data_line_shape='vh',
                        layout_template='seaborn',
                        layout_title=config.eg[tag].label,
                        layout_yaxis_title="Потребленная ЭЭ, кВт*ч",
                    )

                    return output_plot_png(fig, filename + ".png")

                elif 'table_show' in request.POST:
                    plot = output_table_show(df_total)

                elif 'table_excel' in request.POST:
                    return output_table_excel(df_total, filename, "Потребленная ЭЭ")

    else:
        ts_to = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        ts_to = ts_to.replace(second=0)

        ts_from = ts_to + datetime.timedelta(days=-1)

        form = DatetimePicker(
            initial={
                'from_time': ts_from,
                'from_date': ts_from.strftime('%Y-%m-%d'),
                'to_time': ts_to,
                'to_date': ts_to.strftime('%Y-%m-%d'),
            },
            choices_tag=Config().electricity_label_choices(),
            choices_field=[
                ['ep_imp', 'Активная энергия (+)'],
                ['eq_imp', 'Реактивная энергия (+)'],
                ['ep_exp', 'Активная энергия (-)'],
                ['eq_exp', 'Реактивная энергия (-)'],
            ],
        )

    return render(
        request, 'electricity/energy.html',
        context={
            'form_header': 'Потребление ЭЭ',
            'plot': plot,
            'form': form,
        })


def electricity_power(request):
    global_view(request)

    plot = ''

    if request.method == 'POST':
        form = DatetimePicker(
            request.POST,
            choices_tag=Config().electricity_label_choices(),
            choices_field=[
                ['p', 'Активная мощность'],
                ['q', 'Реактивная мощность'],
            ],
        )

        if form.is_valid():
            config = Config()

            # конструируем время от и до
            tzinfo = pytz.timezone(settings.TIME_ZONE)
            ts_from = datetime.datetime.combine(form.cleaned_data['from_date'],
                                                form.cleaned_data['from_time'])
            ts_to = datetime.datetime.combine(form.cleaned_data['to_date'],
                                              form.cleaned_data['to_time'])
            ts_from = tzinfo.localize(ts_from)
            ts_to = tzinfo.localize(ts_to)

            if ts_from >= ts_to:
                return alert_timerange(form, request, "Пиковая мощность")

            tag = form.cleaned_data['tag']

            logger.debug(f"try to load tag: {tag}, from: {ts_from}, to: {ts_to},"
                         f"aggwindow: {form.cleaned_data['aggregate_window']}")

            if tag in config.e:
                df = query_data(
                    config=config,
                    ts_from=ts_from,
                    ts_to=ts_to,
                    measurement=config.e[tag].influxdb_meas,
                    field=form.cleaned_data['field'],
                    aggwindow=form.cleaned_data['aggregate_window'],
                    aggfunc='max',
                )

                if len(df) == 0:
                    return alert_nodata(form, request, "Пиковая мощность")

                df['_value'] = pd.to_numeric(df['_value'])

                # переименовываем стобцы
                df = df.rename(columns={'_value': config.e[tag].label})

                df = df.set_index('_time')
                df = df.sort_index(axis=0)
                df.index = df.index.tz_convert(settings.TIME_ZONE)
                df.index = df.index.rename('Время')

                df = df.drop(columns=['result', 'table', '_field', '_measurement', '_start', '_stop',
                                      'aggfunc', 'aggwindow', 'datatype'])

                # имя файла для экспорта
                filename = get_filename(config.e[tag].label, ts_from, ts_to)

                plot_show = 'plot_show' in request.POST
                plot_png = 'plot_png' in request.POST

                if plot_show or plot_png:
                    if plot_show:
                        layout_template = get_plotly_template(request.session['theme'])
                    else:
                        layout_template = get_plotly_template('white')

                if 'plot_show' in request.POST:
                    fig = plot_stacked_scatter(
                        df=df,
                        data_line_shape='linear',
                        layout_template=get_plotly_template(request.session['theme']),
                        layout_title=config.e[tag].label,
                        layout_yaxis_title="Пиковая мощность, кВт",
                    )

                    plot = output_plot_show(fig)

                elif 'plot_png' in request.POST:
                    fig = plot_stacked_scatter(
                        df=df,
                        data_line_shape='linear',
                        layout_template='seaborn',
                        layout_title=config.e[tag].label,
                        layout_yaxis_title="Пиковая мощность, кВт",
                    )

                    return output_plot_png(fig, filename + ".png")

                elif 'table_show' in request.POST:
                    plot = output_table_show(df)

                elif 'table_excel' in request.POST:
                    return output_table_excel(df, filename, "Пиковая мощность")

    else:
        ts_to = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        ts_to = ts_to.replace(second=0)

        ts_from = ts_to + datetime.timedelta(days=-1)

        form = DatetimePicker(
            initial={
                'from_time': ts_from,
                'from_date': ts_from.strftime('%Y-%m-%d'),
                'to_time': ts_to,
                'to_date': ts_to.strftime('%Y-%m-%d'),
            },
            choices_tag=Config().electricity_label_choices(),
            choices_field=[
                ['p', 'Активная мощность'],
                ['q', 'Реактивная мощность'],
            ],
        )

    return render(
        request, 'electricity/energy.html',
        context={
            'form_header': 'Пиковая мощность',
            'plot': plot,
            'form': form,
        })


def electricity_quality(request):
    global_view(request)

    choices_tag = Config().electricity_label_choices()

    choices_field = [
        ['v12,v23,v31', 'Напряжение линейное'],
        ['v12', 'Напряжение линейное V12'],
        ['v23', 'Напряжение линейное V23'],
        ['v31', 'Напряжение линейное V31'],
        ['i1,i2,i3', 'Ток фазный'],
        ['i1', 'Ток фазный I1'],
        ['i2', 'Ток фазный I2'],
        ['i3', 'Ток фазный I3'],
        ['p1,p2,p3,p', 'Активная мощность'],
        ['q1,q2,q3,q', 'Реактивная мощность'],
        ['pf1,pf2,pf3', 'Коэффициент мощности (cos fi)'],
        ['f', 'Частота'],
    ]

    plot = ''

    if request.method == 'POST':
        form = DatetimePicker(
            request.POST,
            choices_tag=choices_tag,
            choices_field=choices_field,
        )

        if form.is_valid():
            config = Config()

            # конструируем время от и до
            tzinfo = pytz.timezone(settings.TIME_ZONE)
            ts_from = datetime.datetime.combine(form.cleaned_data['from_date'],
                                                form.cleaned_data['from_time'])
            ts_to = datetime.datetime.combine(form.cleaned_data['to_date'],
                                              form.cleaned_data['to_time'])
            ts_from = tzinfo.localize(ts_from)
            ts_to = tzinfo.localize(ts_to)

            if ts_from >= ts_to:
                return alert_timerange(form, request, "Показатели качества ЭЭ")

            measurement = form.cleaned_data['tag']
            fields = form.cleaned_data['field']

            # measurement label
            meas_label = ""
            for cf in choices_tag:
                if cf[0] == measurement:
                    meas_label = cf[1]
                    break

            # fields label
            fields_label = ""
            for cf in choices_field:
                if cf[0] == fields:
                    fields_label = cf[1]
                    break

            logger.debug(f"try to load tag: {measurement}, from: {ts_from}, to: {ts_to}, "
                         f"fields: {fields}, "
                         f"aggwindow: {form.cleaned_data['aggregate_window']}")

            if measurement in config.e:
                several_fields = len(fields.split(',')) > 1

                # подпись для вертикальной оси
                field_0 = fields.split(',')[0]
                if field_0 in ['ep_imp', 'ep_exp']:
                    plot_layout_yaxis_title = "Электроэнергия, [Вт·ч]"
                elif field_0 in ['eq_imp', 'eq_exp']:
                    plot_layout_yaxis_title = "Электроэнергия, [ВАр·ч]"
                elif field_0 in ['f', ]:
                    plot_layout_yaxis_title = "Частота, [Гц]"
                elif field_0 in ['i1', 'i2', 'i3']:
                    plot_layout_yaxis_title = "Ток, [А]"
                elif field_0 in ['p1', 'p2', 'p3', 'p']:
                    plot_layout_yaxis_title = "Мощность, [Вт]"
                elif field_0 in ['pf1', 'pf2', 'pf3']:
                    plot_layout_yaxis_title = "Коэффициент мощности"
                elif field_0 in ['q1', 'q2', 'q3', 'q']:
                    plot_layout_yaxis_title = "Мощность, [ВАр]"
                elif field_0 in ['s1', 's2', 's3', 's']:
                    plot_layout_yaxis_title = "Мощность, [ВА]"
                elif field_0 in ['v12', 'v23', 'v31']:
                    plot_layout_yaxis_title = "Напряжение, [В]"
                else:
                    plot_layout_yaxis_title = "---"

                if several_fields:
                    df = query_data(
                        config=config,
                        ts_from=ts_from,
                        ts_to=ts_to,
                        measurement=config.e[measurement].influxdb_meas,
                        field=fields,
                        aggwindow=form.cleaned_data['aggregate_window'],
                        aggfunc='mean',
                    )

                else:
                    df = query_data(
                        config=config,
                        ts_from=ts_from,
                        ts_to=ts_to,
                        measurement=config.e[measurement].influxdb_meas,
                        field=fields,
                        aggwindow=form.cleaned_data['aggregate_window'],
                        aggfunc='mean,max,min',
                    )

                if len(df) == 0:
                    return alert_nodata(form, request, "Показатели качества ЭЭ")

                if several_fields:
                    df['_value'] = pd.to_numeric(df['_value'])
                    df = df.pivot_table(index="_time", columns='_field', values='_value')
                else:
                    df['_value'] = pd.to_numeric(df['_value'])
                    df = df.pivot_table(index="_time", columns='aggfunc', values='_value')

                df = df.sort_index(axis=0)
                df.index = df.index.tz_convert(settings.TIME_ZONE)
                df.index = df.index.rename('Время')

                # имя файла для экспорта
                filename = get_filename(config.e[measurement].label, ts_from, ts_to)

                plot_show = 'plot_show' in request.POST
                plot_png = 'plot_png' in request.POST

                if plot_show or plot_png:
                    if plot_show:
                        layout_template = get_plotly_template(request.session['theme'])
                    else:
                        layout_template = get_plotly_template('white')

                    if several_fields:
                        data = []

                        for col in df.columns:
                            data.append(
                                go.Scatter(
                                    x=df.index,
                                    y=df[col],
                                    name=col,
                                )
                            )

                        plot = go.Figure(
                            data=data,
                            layout=go.Layout(
                                template=layout_template,
                                title=f"{meas_label}. {fields_label}",
                                yaxis=go.layout.YAxis(
                                    title=plot_layout_yaxis_title,
                                )
                            )
                        )
                    else:
                        color_error_range = plotly_hex_to_rgba(
                            pio.templates[pio.templates.default].layout['colorway'][0], 0.2)

                        plot = go.Figure(
                            data=[
                                go.Scatter(
                                    name='',
                                    x=df.index,
                                    y=df['mean'],
                                ),
                                go.Scatter(
                                    line=go.scatter.Line(
                                        color=color_error_range,
                                        width=0,
                                    ),
                                    name='min',
                                    x=df.index,
                                    y=df['min'],
                                ),
                                go.Scatter(
                                    fill='tonexty',
                                    fillcolor=color_error_range,
                                    line=go.scatter.Line(
                                        color=color_error_range,
                                        width=0,
                                    ),
                                    name='max',
                                    x=df.index,
                                    y=df['max'],
                                ),
                            ],
                            layout=go.Layout(
                                template=layout_template,
                                title=f"{meas_label}. {fields_label}",
                                showlegend=False,
                                yaxis=go.layout.YAxis(
                                    title=plot_layout_yaxis_title,
                                )
                            )
                        )

                    if plot_show:
                        plot = plot.to_html(
                            full_html=False,
                            config={'displayModeBar': True, 'displaylogo': False, 'showTips': False}
                        )

                        plot = '<div class="h-100 pb-4">' + plot[5:]
                    elif plot_png:
                        return FileResponse(
                            BytesIO(plot.to_image(format='png', width=1200, height=800)),
                            as_attachment=True,
                            content_type="image/png",
                            filename=filename)

                elif 'table_show' in request.POST:
                    plot = output_table_show(df)

                elif 'table_excel' in request.POST:
                    return output_table_excel(df, filename, f"{meas_label}. {fields_label}")
    else:
        ts_to = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        ts_to = ts_to.replace(second=0)

        ts_from = ts_to + datetime.timedelta(days=-1)

        form = DatetimePicker(
            initial={
                'from_time': ts_from,
                'from_date': ts_from.strftime('%Y-%m-%d'),
                'to_time': ts_to,
                'to_date': ts_to.strftime('%Y-%m-%d'),
            },
            choices_tag=Config().electricity_label_choices(),
            choices_field=choices_field
        )

    return render(
        request, 'electricity/energy.html',
        context={
            'form_header': 'Показатели качества ЭЭ',
            'plot': plot,
            'form': form,
        })


def alert_nodata(form, request, form_header):
    return render(
        request, 'electricity/energy.html',
        context={
            'plot': f"""
                <div class='alert alert-danger' role='alert'>
                    По указанным параметрам данных нет!
                </div>""",
            'form_header': form_header,
            'form': form,
        })


def alert_timerange(form, request, form_header):
    return render(
        request, 'electricity/energy.html',
        context={
            'plot': f"""
                <div class='alert alert-danger' role='alert'>
                    Конечная дата должна быть больше начальной!
                </div>""",
            'form_header': form_header,
            'form': form,
        })


def plotly_hex_to_rgba(color_hex: str, alpha: float) -> str:
    color_rgb = 'rgba('
    for i in (0, 2, 4):
        color_rgb += str(int(color_hex.lstrip('#')[i:i + 2], 16)) + ', '
    color_rgb += f'{alpha})'
    return color_rgb
