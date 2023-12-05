import logging

from textual.widgets import DataTable
from textual.widgets.data_table import RowDoesNotExist
from textual.reactive import reactive


from mactop.metrics_store import metrics


logger = logging.getLogger(__name__)


class TaskTable(DataTable):
    tasks = reactive([])
    # PID must be the first and can not change
    # used for unique key for location
    show_columns = ["pid", "name", "energy_impact", "cputime_ns"]

    def __init__(self, refresh_interval, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refresh_interval = refresh_interval

    def on_mount(self) -> None:
        self.add_columns(*self.show_columns)
        self.set_interval(self.refresh_interval, self.update_tasks)
        self.cursor_type = "row"

    def update_tasks(self) -> None:
        if tasks := metrics.get_powermetrics().tasks:
            self.tasks = tasks

    def watch_tasks(self, tasks) -> None:
        logger.debug("tasks: %d", len(tasks))
        if not tasks:
            return

        try:
            old_cursor_row_key = self.get_cursor_row_key()
        except RowDoesNotExist:
            old_cursor_row_key = None

        existing_keys = set(list((k) for k in self.rows.keys()))
        for task in tasks:
            self._update_task(task, existing_keys)

        new_keys = set(str(t["pid"]) for t in tasks)

        for key in existing_keys:
            if key not in new_keys:
                self.remove_row(key)

        if old_cursor_row_key and old_cursor_row_key in new_keys:
            self.reset_cursor(old_cursor_row_key)

    def get_cursor_row_key(self):
        row_index = self.cursor_coordinate.row
        if not row_index:  # 0 means no rows at the beginning
            return
        row = self.get_row_at(row_index=row_index)
        return row[0]

    def reset_cursor(self, old_cursor_row_key):
        index = self.get_row_index(old_cursor_row_key)
        self.move_cursor(row=index, animate=True)

    def _update_task(self, task, existing_keys):
        row_key = str(task["pid"])

        task_existing = row_key in existing_keys

        if not task_existing:
            self.add_row(*[task[key] for key in self.show_columns], key=row_key)
        else:
            for col in self.show_columns:
                self.update_cell(row_key, col, task[col])
