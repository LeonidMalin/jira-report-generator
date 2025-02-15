from typing import Any

from jinja2 import Template
from jira import Issue
from pandas import DataFrame

from ..constants import Status
from .tags import Table


def get_dataframe(data: list[Issue]) -> DataFrame:
    """Construct dataframe from fetched data."""
    result = []

    for item in data:
        estimate = (
            item.fields.timeoriginalestimate / 60 / 60
            if item.fields.timeoriginalestimate
            else 0
        )
        spent = (
            item.fields.timespent / 60 / 60
            if item.fields.timespent
            else 0
        )
        release_date = [
            getattr(v, "releaseDate", None)
            for v
            in item.fields.fixVersions
        ]

        result.append({
            "id": item.id,
            "key": item.key,
            "status": item.fields.status,
            "summary": item.fields.summary,
            "assignee": item.fields.assignee,
            "components": item.fields.components,
            "estimate": estimate,
            "spent": spent,
            "ratio": (
                round(spent / estimate, 2)
                if spent and estimate
                else 0
            ),
            "versions": item.fields.fixVersions,
            "link": item.permalink(),
            "type": item.fields.issuetype,
            "parent": getattr(item.fields, "parent", None),
            "release_date": release_date[0] if release_date else None,
        })

    return DataFrame(result)


def get_versioned_issues(df: DataFrame) -> DataFrame:
    return df[df["versions"].apply(lambda x: len(x) > 0)].sort_values(
        by=["release_date", "id"],
    )


def render_template(
    tables: list[Table],
    title: str,
    template: Template,
) -> str:
    """Render template."""
    sections = map(str, tables)

    return template.render(
        title=title,
        sections=sections,
    )


def prepare_components_data(issues_dataframe: DataFrame):
    """Prepare components data for usage."""
    return sorted(list(filter(
        lambda x: hasattr(x, "name"),
        issues_dataframe.components.explode().unique().tolist()
    )), key=lambda x: x.id)


def prepare_not_finished_statuses_data(issues_dataframe: DataFrame):
    """Prepare statuses data for usage."""
    # collect used statuses
    statuses = issues_dataframe.status.explode().unique().tolist()

    # not finished statuses
    return list(filter(lambda x: x.name in (
        Status.IN_PROGRESS.value,
        Status.READY_FOR_DEVELOPMENT.value,
    ), statuses))


def prepare_statuses_table_data(
    issues_dataframe: DataFrame,
) -> DataFrame:
    """Prepare initial data for statuses table rendering."""
    components = prepare_components_data(issues_dataframe)

    return issues_dataframe[issues_dataframe["components"].apply(
        lambda x: len(x) > 0 and set(x).issubset(components),
    )]


def prepare_assignees_table_data(issues_dataframe: DataFrame) -> DataFrame:
    """Prepare initial data for assignees table rendering."""
    not_finished_statuses = prepare_not_finished_statuses_data(
        issues_dataframe,
    )
    # assignees table
    return issues_dataframe[issues_dataframe["status"].apply(
        lambda x: x in not_finished_statuses
    )]


def prepare_issues_table_data(
    issues_dataframe: DataFrame,
    component: Any,
) -> DataFrame:
    """Prepare initial data for issues table rendering."""
    return issues_dataframe[issues_dataframe["components"].apply(
        lambda x: component in x
    )]


def prepare_backlog_table_data(issues_dataframe: DataFrame) -> DataFrame:
    """Prepare initial data for backlog table rendering."""
    return issues_dataframe[
        issues_dataframe["versions"].apply(lambda x: len(x) == 0)
    ].sort_values("id")
