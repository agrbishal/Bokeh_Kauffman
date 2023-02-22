from bokeh.models import BooleanFilter, CDSView, ColumnDataSource, TapTool
from bokeh.plotting import figure, output_file, show
from bokeh.models.callbacks import CustomJS
from bokeh.models import CategoricalColorMapper, Legend, DataTable, DateFormatter, TableColumn, MultiChoice
from bokeh.io import curdoc
from bokeh.layouts import column, layout

import pandas as pd
import matplotlib.pyplot as plt

import bokeh.palettes as bp

# For running in codespaces bokeh serve --show Jan08.py 
# --allow-websocket-origin=agrbishal-fictional-telegram-666wq7r7q7vfr5xp-5006.preview.app.github.dev

df_tsne = pd.read_csv('tsne_group_data.csv', index_col=0)
df_tsne.columns = ['tsne_coor0', 'tsne_coor1', 'stay_id', 'group']

df_heart = pd.read_csv('heart_data.csv', index_col=0)

# preset color for each subject
numcolors = len(df_heart['subject_id'].unique())

colors = list(bp.magma(numcolors))

df_heart.subject_id = df_heart.subject_id.astype(str)
df_heart.stay_id = df_heart.stay_id.astype(str)

subject_dict_list = df_heart['subject_id'].unique()
color_dict_heart = {subject_dict_list[i]: colors[i] for i in range(len(subject_dict_list))}

df_heart['color_id'] = '#D3D3D3'

interpolated_hr_series = df_heart.groupby("subject_id")['heart_rate']. \
apply(lambda group: group.interpolate(method='linear', limit_direction='both', axis=0))
df_heart['ip_heart_rate'] = interpolated_hr_series

### plot

TOOLTIPS_HEART = [
("heart_rate", "@heart_rate"),
("subject_id", "@subject_id"),
("stay_id", "@stay_id")
]

TOOLTIPS_TSNE = [
("stay_id", "@stay_id"),
("group", "@group")
]

data_table = 0

subject_id_list = []

def callback_heart(attr, old, new):
    global source_heart
    global layout_
    global subject_id_list
    try:
        # For box select selecting multiple data points
        source_heart_indices = source_heart.selected.indices
        # Adding the data in the set for optimization 
        subject_ids = set()
        # checking subject ids for every data pont for distinc+t ids
        for ele in source_heart_indices:
            subject_ids.add(source_heart.data.get('subject_id')[ele])

        for subject_id in subject_ids:
            if subject_id in subject_id_list:
                subject_id_list.remove(subject_id)
            else:
                subject_id_list.append(subject_id)

        callback_multisource_heart(subject_id_list)

    except Exception as e:
        print(f"Not clicked on the circle ! {e}")
        pass


def callback_multisource_heart(subject_ids):
    global source_heart
    global layout_
    global subject_id_list
    try:
        subject_id_list = subject_ids

        not_subject_id_list = list(set(subject_dict_list) - set(subject_id_list))

        color_dict_heart_copy = color_dict_heart.copy()
        for subject in not_subject_id_list:
            color_dict_heart_copy[subject] = '#D3D3D3'


        df_heart['color_id'] = list(df_heart['subject_id'].apply(lambda x: color_dict_heart_copy[x]))

        df1 = df_heart[df_heart['subject_id'].isin(not_subject_id_list)]
        df2 = df_heart[df_heart['subject_id'].isin(subject_id_list)] 
        res_df = df1.append(df2)

        p = figure(title="Crystalloids input on HR plot for SubjectIDs in ICU", 
        x_axis_label='deltas',
        y_axis_label='heart_rate', width=1400, aspect_scale=5, tooltips=TOOLTIPS_HEART, tools=["tap", "box_select"])
        source_heart = ColumnDataSource(data=res_df)

        p.circle('deltas', 'ip_heart_rate', source=source_heart, size=4, color = 'color_id')
        source_heart.selected.on_change('indices', callback_heart)

        df = df_heart.copy()
        df = df[df['subject_id'].isin(subject_id_list)]
        grp_list = df.subject_id.unique()

        for i in range(len(grp_list)):
            dummy_df = df[df['subject_id'] == grp_list[i]].sort_values(by= ['deltas'])
            ccol = dummy_df['color_id'].unique().tolist()[0]
            source_2 = ColumnDataSource(
                data={'deltas':dummy_df.deltas,
                    'subject_id':dummy_df.subject_id,
                    'color_id':dummy_df.color_id,
                    'ip_heart_rate':dummy_df.ip_heart_rate})

            p.line(x='deltas',
                    y='ip_heart_rate',
                    source=source_2,
                    legend_label = grp_list[i],
                    color = ccol)


        table_data = ColumnDataSource({'SUBJECT ID' :  subject_id_list})
        columns = [
            TableColumn(field="SUBJECT ID", title="SUBJECT ID")
        ]

        data_table = DataTable(source=table_data, columns=columns, width=400, height=280)
        layout_.children.pop()
        layout_.children.pop()

        layout_.children.append(p)
        layout_.children.append(data_table)

    except Exception as e:
        print(f"Not clicked on the circle ! {e}")
        pass


def multi_choice_callback(attr, old, new):
    try:

        global source_heart
        global source_tsne
        global layout_

        values = multi_choice.value
        multi_choice_stay_id = df_tsne[df_tsne['group'].isin(values)]['stay_id'].tolist()
        multi_choice_subject_id = list(set(df_heart[df_heart['stay_id'].isin(multi_choice_stay_id)]['subject_id'].tolist()))

        not_values = list(set(df_tsne['group'].tolist()) - set(values))

        color_dict_tsne_copy = color_dict_tsne.copy()
        for value in not_values:
            color_dict_tsne_copy[value] = '#D3D3D3'

        df_tsne['group_color'] = df_tsne['group'].apply(color_dict_tsne_copy.get)
        p_tsne = figure(title="T-SNE and group plot", 
        plot_width=800, 
        plot_height=400,
        x_axis_label='tsne_coor0',
        y_axis_label='tsne_coor1', aspect_scale=5, tooltips=TOOLTIPS_TSNE, tools=["tap", "box_select"])

        source_tsne = ColumnDataSource(data=df_tsne)
        p_tsne.circle('tsne_coor0', 'tsne_coor1', source=source_tsne, size=7, color = 'group_color', legend_group = 'group', nonselection_fill_alpha=0.6, selection_color="group_color", nonselection_fill_color="group_color")
        source_tsne.selected.on_change('indices', tsne_click_callback)

        layout_.children[1] = p_tsne

        callback_multisource_heart(multi_choice_subject_id)
    except Exception as e:
        print(f"{e}")
        pass

def tsne_click_callback(attr, old, new):
    global source_tsne
    global subject_id_list
    source_tsne_indices = source_tsne.selected.indices
    # Adding the data in the set for optimization 
    subject_ids = set()
    # checking subject ids for every data pont for distinc+t ids
    for ele in source_tsne_indices:
        stay_id = source_tsne.data.get('stay_id')[ele]
        subject_ids.add(df_heart.loc[df_heart['stay_id'] == stay_id]['subject_id'].unique()[0])


    for subject_id in subject_ids:
        if subject_id in subject_id_list:
            subject_id_list.remove(subject_id)
        else:
            subject_id_list.append(subject_id)

    callback_multisource_heart(subject_id_list)
    # print(f"{e}")

# preset color for each subject
group_numcolors = len(df_tsne['group'].unique())

group_colors = list(bp.plasma(group_numcolors))

df_tsne.stay_id = df_tsne.stay_id.astype(str)
df_tsne.group = df_tsne.group.astype(str)

stay_dict_list = df_tsne['stay_id'].unique()
color_dict_tsne = {df_tsne['group'].unique()[i]: group_colors[i] for i in range(len(group_colors))}

df_tsne['group_color'] = df_tsne['group'].apply(color_dict_tsne.get)

p_tsne = figure(title="T-SNE and group plot", 
x_axis_label='tsne_coor0',
y_axis_label='tsne_coor1', aspect_scale=5, tooltips=TOOLTIPS_TSNE, tools=["tap", "box_select"])

source_tsne = ColumnDataSource(data=df_tsne)

p_tsne.circle('tsne_coor0', 'tsne_coor1', source=source_tsne, size=7, color = 'group_color', legend_group = 'group', nonselection_fill_alpha=0.6,
selection_color="group_color", nonselection_fill_color="group_color")
source_tsne.selected.on_change('indices', tsne_click_callback)


OPTIONS = df_tsne['group'].unique().tolist()

multi_choice = MultiChoice(value=OPTIONS, options=OPTIONS)
multi_choice.on_change('value', multi_choice_callback)

p = figure(title="Crystalloids input on HR plot for SubjectIDs in ICU", 
x_axis_label='deltas',
y_axis_label='heart_rate', width=1400, aspect_scale=5, tooltips=TOOLTIPS_HEART, tools=["tap", "box_select"])

source_heart = ColumnDataSource(data=df_heart)

p.circle('deltas', 'ip_heart_rate', source=source_heart, size=4, color = 'color_id')
source_heart.selected.on_change('indices', callback_heart)

table_data = ColumnDataSource({'SUBJECT ID' :  subject_id_list})
columns = [
        TableColumn(field="SUBJECT ID", title="SUBJECT ID")
    ]
data_table = DataTable(source=table_data, columns=columns, width=400, height=280)

layout_ = layout([multi_choice, p_tsne, p, data_table])

curdoc().add_root(layout_)