# streamlit_crm_dashboard.py
# Dashboard Streamlit adaptado para datasets reais (MOXOTÓ)
# Inclui análises estratégicas: Forecast, Motivo de Perda, Ranking de Vendedores, Conversão por Etapa

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide", page_title="CRM Analytics - Dashboard")

st.title("Dashboard Analytics MOXOTÓ")

# Sidebar: upload dos datasets
st.sidebar.header("Dados")
tasks_file = st.sidebar.file_uploader("Upload: Tarefas (CSV)", type=["csv"], key="tasks")
deals_file = st.sidebar.file_uploader("Upload: Negociações (CSV)", type=["csv"], key="deals")

# Função para carregar dados com parsing de datas
def load_csv(file):
    return pd.read_csv(file, sep=None, engine="python")

# Função para parsear datas (dd/mm/yyyy)
def parse_date(df, col, new_col=None):
    if col in df.columns:
        if new_col is None:
            new_col = col
        df[new_col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
    return df

# Função utilitária para exportar DataFrame como CSV
def to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Carregar datasets
if tasks_file and deals_file:
    tasks_df = load_csv(tasks_file)
    deals_df = load_csv(deals_file)
else:
    st.info("Faça upload dos arquivos 'TAREFAS MOXOTÓ.csv' e 'NEGOCIAÇÕES - MOXOTÓ.csv'")
    st.stop()

# Parse de datas relevantes
tasks_df = parse_date(tasks_df, 'Data de criação', 'created_at')
tasks_df = parse_date(tasks_df, 'Data agendada', 'scheduled_at')
tasks_df = parse_date(tasks_df, 'Data da conclusão', 'completed_at')

deals_df = parse_date(deals_df, 'Data de criação', 'deal_created_at')
deals_df = parse_date(deals_df, 'Data do primeiro contato', 'first_contact_at')
deals_df = parse_date(deals_df, 'Data do último contato', 'last_contact_at')
deals_df = parse_date(deals_df, 'Data de fechamento', 'closed_at')
deals_df = parse_date(deals_df, 'Previsão de fechamento', 'forecast_close_at')

# Criar chave de merge
# Negociações: Nome | Tarefas: Negociação vinculada
tasks_df['Negociação vinculada_norm'] = tasks_df['Negociação vinculada'].astype(str).str.strip().str.upper()
deals_df['Nome_norm'] = deals_df['Nome'].astype(str).str.strip().str.upper()

# Tarefas por negociação
tasks_per_deal = tasks_df.groupby('Negociação vinculada_norm').size().rename('tasks_count').reset_index()

# Tempo médio de conclusão de tarefas
completed_tasks = tasks_df[tasks_df['completed_at'].notna()].copy()
completed_tasks['task_duration_days'] = (completed_tasks['completed_at'] - completed_tasks['created_at']).dt.total_seconds() / 86400
avg_task_duration = completed_tasks.groupby('Negociação vinculada_norm')['task_duration_days'].mean().rename('avg_task_duration_days').reset_index()

# Merge com negociações
metrics_deals = deals_df.copy()
metrics_deals = metrics_deals.merge(tasks_per_deal, left_on='Nome_norm', right_on='Negociação vinculada_norm', how='left')
metrics_deals = metrics_deals.merge(avg_task_duration, left_on='Nome_norm', right_on='Negociação vinculada_norm', how='left')

metrics_deals['tasks_count'] = metrics_deals['tasks_count'].fillna(0)
metrics_deals['avg_task_duration_days'] = metrics_deals['avg_task_duration_days'].fillna(0)

# Ciclos de vendas
metrics_deals['time_to_first_contact_days'] = (metrics_deals['first_contact_at'] - metrics_deals['deal_created_at']).dt.total_seconds() / 86400
metrics_deals['time_to_close_days'] = (metrics_deals['closed_at'] - metrics_deals['deal_created_at']).dt.total_seconds() / 86400

# Filtros
st.sidebar.header("Filtros")
filter_responsible = st.sidebar.multiselect("Responsável", options=metrics_deals['Responsável'].dropna().unique())
filter_source = st.sidebar.multiselect("Fonte", options=metrics_deals['Fonte'].dropna().unique())
filter_stage = st.sidebar.multiselect("Etapa", options=metrics_deals['Etapa'].dropna().unique())

# Filtro por datas (usando a data de criação da negociação)
min_date = metrics_deals['deal_created_at'].min()
max_date = metrics_deals['deal_created_at'].max()
date_range = st.sidebar.date_input(
    "Período da Negociação (Data de Criação)",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

filtered = metrics_deals.copy()
if filter_responsible:
    filtered = filtered[filtered['Responsável'].isin(filter_responsible)]
if filter_source:
    filtered = filtered[filtered['Fonte'].isin(filter_source)]
if filter_stage:
    filtered = filtered[filtered['Etapa'].isin(filter_stage)]
if date_range:
    start_date, end_date = date_range
    filtered = filtered[
        (filtered['deal_created_at'] >= pd.to_datetime(start_date)) &
        (filtered['deal_created_at'] <= pd.to_datetime(end_date))
    ]

# KPIs — agora usando o DataFrame filtrado!
total_deals = len(filtered)
won_deals = (filtered['Estado'].str.lower() == 'vendida').sum()
loss_deals = (filtered['Estado'].str.lower() == 'perdida').sum()
avg_value = filtered['Valor Único'].mean()
avg_tasks = filtered['tasks_count'].mean()
conversion_rate = (won_deals / total_deals) * 100 if total_deals > 0 else 0
total_revenue = filtered[filtered['Estado'].str.lower() == 'vendida']['Valor Único'].sum()
avg_sales_cycle = filtered[filtered['Estado'].str.lower() == 'vendida']['time_to_close_days'].mean()


# --- Abas do Dashboard ---
tab_kpi, tab_funnel, tab_tasks, tab_strategy, tab_detail = st.tabs([
    "KPIs Gerais",
    "Funil de Vendas",
    "Tarefas",
    "Estratégico",
    "Detalhamento"
])

with tab_kpi:
    st.header("KPIs Gerais")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Negociações", f"{total_deals}")
    col2.metric("Vendidas", f"{won_deals}")
    col3.metric("Perdidas", f"{loss_deals}")
    col4.metric("Taxa de Conversão", f"{conversion_rate:.2f}%")

    st.markdown("---")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Receita Total (Vendido)", f"R$ {total_revenue:,.2f}")
    col6.metric("Ticket Médio", f"R$ {avg_value:,.2f}")
    col7.metric("Ciclo Médio de Venda (dias)", f"{avg_sales_cycle:.1f}" if not pd.isna(avg_sales_cycle) else "N/A")
    col8.metric("Tarefas/Negociação", f"{avg_tasks:.1f}")

with tab_funnel:
    st.header("Funil de Vendas")
    funnel = filtered.groupby('Etapa').agg({'Nome':'count','Valor Único':'sum'}).reset_index().rename(columns={'Nome':'count'})
    fig_funnel = px.bar(funnel, x='Etapa', y='count', text='count', title='Negociações por Etapa')
    st.plotly_chart(fig_funnel, use_container_width=True)

with tab_tasks:
    st.header("Tarefas — Distribuição")

    # Filtra as tarefas com base nas negociações já filtradas
    filtered_tasks = tasks_df[tasks_df['Negociação vinculada_norm'].isin(filtered['Nome_norm'])]

    if not filtered_tasks.empty:
        # KPIs de Tarefas
        total_tasks_filtered = len(filtered_tasks)
        completed_tasks_filtered = (filtered_tasks['Status'].str.lower() == 'concluída').sum()
        # Considera atrasada se a data agendada passou e não foi concluída
        overdue_tasks = filtered_tasks[
            (filtered_tasks['scheduled_at'] < pd.to_datetime('today')) &
            (filtered_tasks['Status'].str.lower() != 'concluída')
        ].shape[0]
        avg_duration = filtered[filtered['avg_task_duration_days'] > 0]['avg_task_duration_days'].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Tarefas", total_tasks_filtered)
        col2.metric("Concluídas", completed_tasks_filtered)
        col3.metric("Atrasadas", overdue_tasks)
        col4.metric("Tempo Médio de Conclusão (dias)", f"{avg_duration:.1f}" if not pd.isna(avg_duration) else "N/A")

        st.markdown("---")

        # Gráficos
        col_tipo, col_status = st.columns(2)
        with col_tipo:
            if 'Tipo' in filtered_tasks.columns:
                ttype = filtered_tasks.groupby('Tipo').size().reset_index(name='count')
                fig_tasks = px.pie(ttype, names='Tipo', values='count', title='Tipos de Tarefa (Filtrado)')
                st.plotly_chart(fig_tasks, use_container_width=True)
        
        with col_status:
            if 'Status' in filtered_tasks.columns:
                status_count = filtered_tasks.groupby('Status').size().reset_index(name='count').sort_values('count', ascending=False)
                fig_status = px.bar(status_count, x='Status', y='count', text_auto=True, title='Status das Tarefas (Filtrado)')
                st.plotly_chart(fig_status, use_container_width=True)

        if 'Responsável pela tarefa' in filtered_tasks.columns:
            resp_count = filtered_tasks.groupby('Responsável pela tarefa').size().reset_index(name='count').sort_values('count', ascending=False)
            fig_resp = px.bar(resp_count, x='Responsável pela tarefa', y='count', text_auto=True, title='Tarefas por Responsável')
            st.plotly_chart(fig_resp, use_container_width=True)
    else:
        st.info("Nenhuma tarefa encontrada para os filtros selecionados.")

with tab_strategy:
    st.header("Previsão de Receita")
    if 'forecast_close_at' in filtered.columns:
        forecast = filtered.copy()
        forecast['month'] = forecast['forecast_close_at'].dt.to_period("M").dt.to_timestamp()
        forecast_grouped = forecast.groupby('month').agg({
            'Valor Único':'sum'
        }).reset_index()
        fig_forecast = px.line(forecast_grouped, x='month', y='Valor Único', markers=True, title='Receita Prevista por Mês')
        st.plotly_chart(fig_forecast, use_container_width=True)

    st.header("Motivos de Perda")
    if 'Motivo de Perda' in filtered.columns:
        loss_reasons = filtered[filtered['Estado'].str.lower() == 'perdida']
        reasons_count = loss_reasons.groupby('Motivo de Perda').size().reset_index(name='count').sort_values('count', ascending=False).head(5)
        fig_loss = px.bar(reasons_count, x='Motivo de Perda', y='count', title='Top 5 Motivos de Perda')
        st.plotly_chart(fig_loss, use_container_width=True)

    st.header("🏆 Ranking de Vendedores")
    leaderboard = filtered.groupby('Responsável').agg({
        'Nome':'count','Valor Único':'sum'
    }).rename(columns={'Nome':'negociações','Valor Único':'valor_total'}).reset_index()
    leaderboard = leaderboard.sort_values('valor_total', ascending=False)
    st.dataframe(leaderboard)

    st.header("Conversão por Etapa do Funil")
    if 'Etapa' in filtered.columns and 'Estado' in filtered.columns:
        conversion = filtered.groupby(['Etapa','Estado']).size().reset_index(name='count')
        fig_conv = px.bar(conversion, x='Etapa', y='count', color='Estado', barmode='group', title='Conversão por Etapa')
        st.plotly_chart(fig_conv, use_container_width=True)

with tab_detail:
    st.header("Detalhamento de Negociações")
    st.dataframe(filtered)
    csv = to_csv(filtered)
    st.download_button("📥 Baixar CSV filtrado", csv, "negociacoes_filtradas.csv", "text/csv")

# Função utilitária para exportar DataFrame como CSV
def to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

st.markdown("---")
st.caption("Dashboard adaptado para datasets MOXOTÓ — inclui análises estratégicas de CRM.")
