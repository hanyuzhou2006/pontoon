"""
Test consistency of calculations between `calculate_stats` and `translation.save()`.
"""
import pytest
from pontoon.base.models import Project, TranslatedResource, Translation
from pontoon.checks.models import (
    Error,
    Warning,
    FailedCheck,
)
from pontoon.test.factories import (
    EntityFactory,
    LocaleFactory,
    ProjectFactory,
    ProjectLocaleFactory,
    ResourceFactory,
    TranslatedResourceFactory,
    UserFactory,
)


@pytest.fixture
def translation_with_error(translation_a):
    Error.objects.create(
        translation=translation_a, library=FailedCheck.Library.PONTOON, message="error"
    )
    return translation_a


@pytest.fixture
def translation_with_warning(translation_a):
    Warning.objects.create(
        translation=translation_a,
        library=FailedCheck.Library.PONTOON,
        message="warning",
    )
    return translation_a


def recalculate_stats(translation):
    """
    Make the full recalculate stats on a TranslatedResource.
    """
    translation.save(update_stats=False)
    translated_resource = TranslatedResource.objects.get(
        resource=translation.entity.resource,
        locale=translation.locale,
    )
    translated_resource.calculate_stats()


def diff_stats(t):
    """
    Update only necessary stats by calculating difference between stats.
    """
    t.save()


@pytest.fixture(
    params=(
        recalculate_stats,
        diff_stats,
    )
)
def stats_update(db, request):
    """
    Wrapper fixture which allows to test both implementations of stats calculations.
    """
    return request.param


@pytest.fixture
def get_stats():
    def f(translation):
        return TranslatedResource.objects.filter(
            resource=translation.entity.resource,
            locale=translation.locale,
        ).aggregated_stats()

    return f


def test_translation_approved(stats_update, get_stats, translation_a):
    translation_a.approved = True
    stats_update(translation_a)

    assert get_stats(translation_a) == {
        "total": 1,
        "approved": 1,
        "pretranslated": 0,
        "unreviewed": 0,
        "warnings": 0,
        "errors": 0,
    }

    translation_a.approved = False
    stats_update(translation_a)

    assert get_stats(translation_a) == {
        "total": 1,
        "approved": 0,
        "pretranslated": 0,
        "unreviewed": 1,
        "warnings": 0,
        "errors": 0,
    }


def test_translation_pretranslated(stats_update, get_stats, translation_a):
    translation_a.pretranslated = True
    stats_update(translation_a)

    assert get_stats(translation_a) == {
        "total": 1,
        "approved": 0,
        "pretranslated": 1,
        "unreviewed": 0,
        "warnings": 0,
        "errors": 0,
    }

    translation_a.pretranslated = False
    translation_a.rejected = True
    stats_update(translation_a)

    assert get_stats(translation_a) == {
        "total": 1,
        "approved": 0,
        "pretranslated": 0,
        "unreviewed": 0,
        "warnings": 0,
        "errors": 0,
    }


def test_translation_with_error(stats_update, get_stats, translation_with_error):
    translation_with_error.approved = True
    stats_update(translation_with_error)

    assert get_stats(translation_with_error) == {
        "total": 1,
        "approved": 0,
        "pretranslated": 0,
        "unreviewed": 0,
        "warnings": 0,
        "errors": 1,
    }

    translation_with_error.approved = False
    translation_with_error.pretranslated = True
    stats_update(translation_with_error)

    assert get_stats(translation_with_error) == {
        "total": 1,
        "approved": 0,
        "pretranslated": 0,
        "unreviewed": 0,
        "warnings": 0,
        "errors": 1,
    }

    translation_with_error.pretranslated = False
    stats_update(translation_with_error)

    assert get_stats(translation_with_error) == {
        "total": 1,
        "approved": 0,
        "pretranslated": 0,
        "unreviewed": 1,
        "warnings": 0,
        "errors": 0,
    }


def test_translation_with_warning(stats_update, get_stats, translation_with_warning):
    translation_with_warning.approved = True
    stats_update(translation_with_warning)

    assert get_stats(translation_with_warning) == {
        "total": 1,
        "approved": 0,
        "pretranslated": 0,
        "unreviewed": 0,
        "warnings": 1,
        "errors": 0,
    }

    translation_with_warning.approved = False
    translation_with_warning.pretranslated = True
    stats_update(translation_with_warning)

    assert get_stats(translation_with_warning) == {
        "total": 1,
        "approved": 0,
        "pretranslated": 0,
        "unreviewed": 0,
        "warnings": 1,
        "errors": 0,
    }

    translation_with_warning.pretranslated = False
    stats_update(translation_with_warning)

    assert get_stats(translation_with_warning) == {
        "total": 1,
        "approved": 0,
        "pretranslated": 0,
        "unreviewed": 1,
        "warnings": 0,
        "errors": 0,
    }


def test_private_project_stats_do_not_update_locale():
    locale = LocaleFactory.create()
    project = ProjectFactory.create(
        visibility=Project.Visibility.PRIVATE,
        repositories=[],
        total_strings=1,
        unreviewed_strings=1,
    )
    project_locale = ProjectLocaleFactory.create(
        project=project,
        locale=locale,
        total_strings=1,
        unreviewed_strings=1,
    )
    resource = ResourceFactory.create(project=project, total_strings=1)
    translated_resource = TranslatedResourceFactory.create(
        resource=resource,
        locale=locale,
        total_strings=1,
        unreviewed_strings=1,
    )
    entity = EntityFactory.create(resource=resource)
    translation = Translation(
        entity=entity,
        locale=locale,
        string="translation",
        user=UserFactory.create(),
    )
    translation.save(update_stats=False)
    locale.aggregate_stats()
    locale.refresh_from_db()

    assert locale.unreviewed_strings == 0

    translation.approved = True
    translation.save()

    locale.refresh_from_db()
    project.refresh_from_db()
    project_locale.refresh_from_db()
    translated_resource.refresh_from_db()

    assert locale.unreviewed_strings == 0
    assert project.approved_strings == 1
    assert project.unreviewed_strings == 0
    assert project_locale.approved_strings == 1
    assert project_locale.unreviewed_strings == 0
    assert translated_resource.approved_strings == 1
    assert translated_resource.unreviewed_strings == 0
