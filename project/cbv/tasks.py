"""
This page handles the cbv methods for task page
"""

import logging
from typing import Any

from django import forms
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.methods import get_subordinates
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaCardView,
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from project.cbv.project_stage import StageDynamicCreateForm
from project.cbv.projects import DynamicProjectCreationFormView
from project.filters import TaskAllFilter
from project.forms import TaskAllForm
from project.methods import you_dont_have_permission
from project.models import Project, ProjectStage, Task
from project.templatetags.taskfilters import task_crud_perm

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class TasksTemplateView(TemplateView):
    """
    view page of the task page
    """

    template_name = "cbv/tasks/task_template_view.html"


@method_decorator(login_required, name="dispatch")
class TaskListView(HorillaListView):
    """
    list view of the page
    """

    model = Task
    filter_class = TaskAllFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "task-list-container"
        self.search_url = reverse("tasks-list-view")

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("project.view_task"):
            employee_id = self.request.user.employee_get
            subordinates = get_subordinates(self.request)
            subordinate_ids = [subordinate.id for subordinate in subordinates]
            project = queryset.filter(
                Q(project__managers=employee_id)
                | Q(project__members=employee_id)
                | Q(project__managers__in=subordinate_ids)
                | Q(project__members__in=subordinate_ids)
            )
            queryset = (
                queryset.filter(
                    Q(task_members=employee_id)
                    | Q(task_managers=employee_id)
                    | Q(task_members__in=subordinate_ids)
                    | Q(task_managers__in=subordinate_ids)
                )
                | project
            )
        return queryset.distinct()

    columns = [
        (_("Task"), "title"),
        (_("Project"), "project"),
        (_("Stage"), "stage"),
        (_("Mangers"), "get_managers"),
        (_("Members"), "get_members"),
        (_("End Date"), "end_date"),
        (_("Status"), "status_column"),
        (_("Description"), "description"),
    ]

    sortby_mapping = [
        ("Task", "title"),
        ("Project", "project__title"),
        ("Stage", "stage"),
        ("End Date", "end_date"),
        ("Status", "status"),
    ]

    action_method = "actions"

    row_status_indications = [
        (
            "todo--dot",
            _("To Do"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('to_do');
                $('#applyFilter').click();
            "
            """,
        ),
        (
            "in-progress--dot",
            _("In progress"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('in_progress');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "completed--dot",
            _("Completed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('completed');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "expired--dot",
            _("Expired"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('expired');
                $('#applyFilter').click();

            "
            """,
        ),
    ]

    row_status_class = "status-{status}"

    row_attrs = """
                hx-get='{task_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
class TasksNavBar(HorillaNavView):
    """
    navbar of teh page
    """

    nav_title = _("Tasks")
    filter_instance = TaskAllFilter()
    filter_form_context_name = "form"
    filter_body_template = "cbv/tasks/task_filter.html"
    search_swap_target = "#listContainer"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        employee = self.request.user.employee_get
        projects = Project.objects.all()
        managers = [
            manager for project in projects for manager in project.managers.all()
        ]
        members = [member for project in projects for member in project.members.all()]
        self.search_url = reverse("tasks-list-view")
        if employee in managers + members or self.request.user.has_perm(
            "project.add_task"
        ):
            self.create_attrs = f"""
                                    onclick = "event.stopPropagation();"
                                    data-toggle="oh-modal-toggle"
                                    data-target="#genericModal"
                                    hx-target="#genericModalBody"
                                    hx-get="{reverse('create-task-all')}"
                                    """

        self.view_types = [
            {
                "type": "list",
                "icon": "list-outline",
                "url": reverse("tasks-list-view"),
                "attrs": """
                        title ='List'
                        """,
            },
            {
                "type": "card",
                "icon": "grid-outline",
                "url": reverse("tasks-card-view"),
                "attrs": """
                          title ='Card'
                          """,
            },
        ]

        if self.request.user.has_perm("project.view_task"):
            self.actions = [
                {
                    "action": _("Archive"),
                    "attrs": """
                            id="archiveTask",
                            style="cursor: pointer;"
                            """,
                },
                {
                    "action": _("Un-Archive"),
                    "attrs": """
                            id="unArchiveTask",
                            style="cursor: pointer;"
                            """,
                },
                {
                    "action": _("Delete"),
                    "attrs": """
                                class="oh-dropdown__link--danger"
                                data-action = "delete"
                                id="deleteTask"
                                style="cursor: pointer; color:red !important"

                                """,
                },
            ]

    group_by_fields = [
        ("project", _("Project")),
        ("stage", _("Stage")),
        ("status", _("Status")),
    ]

@method_decorator(login_required, name="dispatch")
class TaskCreateForm(HorillaFormView):
    form_class = TaskAllForm
    model = Task
    template_name = "cbv/tasks/task_form.html"
    new_display_title = _("Create Task")
    def setup(self, request, *args, **kwargs):
        self.request = request
        return super().setup(request, *args, **kwargs)
    def has_project_access(self, user, project):
        return (
            user.is_superuser or
            user.employee_get in project.managers.all() or
            user.employee_get in project.members.all()
        )
    def has_task_access(self, user, task):
        return user.is_superuser or user.employee_get in task.task_managers.all()
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.object = None
        form = self.get_form()
        if request.GET.get("project_task"):
            project_id = request.GET.get("project_task")
            stage_id = (
                ProjectStage.objects.filter(project_id=project_id)
                .order_by("sequence")
                .values_list("id", flat=True)
                .first()
            )
            form.fields["project"].initial = project_id
            form.fields["stage"].initial = stage_id
            stages = ProjectStage.objects.filter(project_id=project_id)
            form.fields["stage"].choices = [(s.pk, s.title) for s in stages]
        elif kwargs.get("stage_id"):
            stage_id = kwargs["stage_id"]
            stage = get_object_or_404(ProjectStage, pk=stage_id)
            project = stage.project
            form.fields["project"].initial = project.id
            form.fields["stage"].initial = stage.id
            stages = ProjectStage.objects.filter(project=project)
            form.fields["stage"].choices = [(s.pk, s.title) for s in stages]
        context = self.get_context_data(form=form)
        return self.render_to_response(context)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get("form", self.get_form())
        project_id = self.kwargs.get("project_id")
        stage_id = self.kwargs.get("stage_id")
        task_id = self.kwargs.get("pk")
        dynamic_project_id = self.request.GET.get("dynamic_project")
        if dynamic_project_id and dynamic_project_id != "dynamic_create":
            stages = ProjectStage.objects.filter(project=dynamic_project_id)
            form.fields["stage"].choices = [("", _("Select Stage"))] + [(s.pk, s.title) for s in stages]
        if task_id and not dynamic_project_id:
            task = form.instance
            if task.project:
                stages = task.project.project_stages.all()
                form.fields["stage"].choices = [("", _("Select Stage"))] + [(s.pk, s.title) for s in stages]
        if stage_id:
            stage = ProjectStage.objects.filter(id=stage_id).first()
            if stage:
                project = stage.project
                form.fields["stage"].initial = stage
                form.fields["stage"].choices = [(stage.id, stage.title)]
                form.fields["project"].initial = project
                form.fields["project"].choices = [(project.id, project.title)]
        elif project_id:
            project = Project.objects.filter(id=project_id).first()
            if project:
                form.fields["project"].initial = project
                form.fields["project"].choices = [(project.id, project.title)]
                stages = ProjectStage.objects.filter(project=project)
                form.fields["stage"].choices = [(s.id, s.title) for s in stages]
        elif form.instance.pk:
            self.form_class.verbose_name = _("Update Task")
            if self.request.GET.get("project_task"):
                form.fields["project"].widget = forms.HiddenInput()
                form.fields["stage"].widget = forms.HiddenInput()
        if not form.fields["project"].choices:
            form.fields["project"].choices = [(p.pk, p.title) for p in Project.objects.all()]
        if not form.fields["stage"].choices:
            form.fields["stage"].choices = [("", _("Select Stage"))]
        context["form"] = form
        return context
    def form_valid(self, form):
        try:
            is_update = bool(form.instance.pk)
            instance = form.save(commit=False)
        # Forcefully inject project & stage if missing
            project = self.request.POST.get("project") or self.kwargs.get("project_id")
            stage = self.request.POST.get("stage") or self.kwargs.get("stage_id")
            if not project:
                raise ValueError("Missing 'project' field.")
            if not stage:
                raise ValueError("Missing 'stage' field.")
            instance.project_id = project
            instance.stage_id = stage
            instance.save()
            form.save_m2m()
            msg = _(f"{instance} Updated") if is_update else _("New Task created")
            messages.success(self.request, msg)
            if self.kwargs.get("stage_id") or self.request.GET.get("project_task"):
                return HttpResponse("<script>location.reload();</script>")
            return HttpResponse("<script>$('#taskFilterButton').click();</script>")
        except Exception as e:
            logger.error("form_valid() failed: %s", str(e))
            logger.error("Traceback:\n%s", traceback.format_exc())
            logger.error("POST data:\n%s", self.request.POST)
            logger.error("Cleaned data:\n%s", getattr(form, 'cleaned_data', {}))
            messages.error(self.request, _("Something went wrong!"))
            return HttpResponse("<script>window.location.reload()</script>")
    def form_invalid(self, form):
        logger.error("Form errors in TaskCreateForm:\n%s", form.errors)
        messages.error(self.request, _("Form submission failed. Please check the fields."))
        return super().form_invalid(form)


class DynamicTaskCreateFormView(TaskCreateForm):

    is_dynamic_create_view = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET:
            project_id = self.request.GET.get("project_id")
            if project_id:
                project = Project.objects.get(id=project_id)
                stages = ProjectStage.objects.filter(project__id=project_id)
                self.form.fields["project"].initial = project
                self.form.fields["project"].choices = [(project.id, project.title)]
                self.form.fields["stage"].queryset = stages
                # self.form.fields["project"].widget = forms.HiddenInput()
        return context


@method_decorator(login_required, name="dispatch")
class TaskDetailView(HorillaDetailedView):
    """
    detail view of the task page
    """

    model = Task
    title = _("Task Details")

    header = {"title": "title", "subtitle": "project", "avatar": "get_avatar"}

    body = [
        (_("Task"), "title"),
        (_("Project"), "project"),
        (_("Stage"), "stage"),
        (_("Task Mangers"), "get_managers"),
        (_("Task Members"), "get_members"),
        (_("Status"), "status_column"),
        (_("End Date"), "end_date"),
        (_("Description"), "description"),
        (_("Document"), "document_col", True),
    ]

    action_method = "detail_view_actions"


@method_decorator(login_required, name="dispatch")
class TaskCardView(HorillaCardView):
    """
    card view of the page
    """

    model = Task
    filter_class = TaskAllFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "task-card"
        self.search_url = reverse("tasks-card-view")
        self.actions = [
            {
                "action": _("Edit"),
                "accessibility": "project.cbv.accessibility.task_crud_accessibility",
                "attrs": """
                        data-toggle = "oh-modal-toggle"
                        data-target = "#genericModal"
                        hx-target="#genericModalBody"
                        hx-get ='{get_update_url}'
                        class="oh-dropdown__link"
                        style="cursor: pointer;"
                        """,
            },
            {
                "action": _("archive_status"),
                "accessibility": "project.cbv.accessibility.task_crud_accessibility",
                "attrs": """
                href="{get_archive_url}"
                        onclick="return confirm('Do you want to {archive_status} this task?')"
                        class="oh-dropdown__link"
                        """,
            },
            {
                "action": _("Delete"),
                "accessibility": "project.cbv.accessibility.task_crud_accessibility",
                "attrs": """
                    onclick="
                                event.stopPropagation()
                                deleteItem({get_delete_url});
                                "
                    class="oh-dropdown__link oh-dropdown__link--danger"
                    """,
            },
        ]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("project.view_task"):
            employee_id = self.request.user.employee_get
            subordinates = get_subordinates(self.request)
            subordinate_ids = [subordinate.id for subordinate in subordinates]
            project = queryset.filter(
                Q(project__managers=employee_id)
                | Q(project__members=employee_id)
                | Q(project__managers__in=subordinate_ids)
                | Q(project__members__in=subordinate_ids)
            )
            queryset = (
                queryset.filter(
                    Q(task_members=employee_id)
                    | Q(task_managers=employee_id)
                    | Q(task_members__in=subordinate_ids)
                    | Q(task_managers__in=subordinate_ids)
                )
                | project
            )
        return queryset.distinct()

    details = {
        "image_src": "get_avatar",
        "title": "{title}",
        "subtitle": "Project Name : {if_project} <br> Stage Name : {stage}<br> End Date : {end_date}",
    }

    card_attrs = """
                hx-get='{task_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    card_status_indications = [
        (
            "todo--dot",
            _("To Do"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('to_do');
                $('#applyFilter').click();
            "
            """,
        ),
        (
            "in-progress--dot",
            _("In progress"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('in_progress');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "completed--dot",
            _("Completed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('completed');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "expired--dot",
            _("Expired"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=status]').val('expired');
                $('#applyFilter').click();

            "
            """,
        ),
    ]

    card_status_class = "status-{status}"


class TasksInIndividualView(TaskListView):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        employee_id = self.request.GET.get("employee_id")
        self.row_attrs = f"""
                hx-get='{{task_detail_view}}?instance_ids={{ordered_ids}}&employee_id={employee_id}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    def get_queryset(self):
        queryset = HorillaListView.get_queryset(self)
        employee_id = self.request.GET.get("employee_id")
        project_id = self.request.GET.get("project_id")
        queryset = queryset.filter(
            Q(task_members=employee_id) | Q(task_manager=employee_id)
        )
        queryset = queryset.filter(project=project_id)
        return queryset

    row_status_indications = None
    bulk_select_option = None
    action_method = None
