import functools
import html
import importlib
import os
import sys
import traceback
import types
import typing as t
from pathlib import Path

import revel

import rio
import rio.app_server.fastapi_server
from rio import icon_registry

from ... import project_config
from .. import nice_traceback


class AppLoadError(Exception):
    pass


def traceback_frame_filter(frame: traceback.FrameSummary) -> bool:
    # Skip frames which are internal to rio
    rio_root = rio.__file__
    assert rio_root.endswith(os.sep + "__init__.py")
    rio_root = rio_root.removesuffix(os.sep + "__init__.py")

    return not frame.filename.startswith(rio_root)


def make_traceback_html(
    *,
    err: t.Union[str, BaseException],
    project_directory: Path,
) -> str:
    error_icon_svg = icon_registry.get_icon_svg("material/error")

    if isinstance(err, str):
        traceback_html = html.escape(err)
    else:
        traceback_html = nice_traceback.format_exception_html(
            err,
            relpath=project_directory,
            frame_filter=traceback_frame_filter,
        )

    return f"""
<div class="rio-traceback rio-dev-tools-background rio-switcheroo-neutral">
    <div class="rio-traceback-header">
        {error_icon_svg}
        <div>Couldn't load the app</div>
    </div>
    <div class="rio-traceback-message">
        Fix the issue below. The app will automatically reload once you save the
        file.
    </div>
    <div class="rio-traceback-traceback">{traceback_html}</div>
    <div class="rio-traceback-footer">
        Need help?
        <div class="rio-traceback-footer-links">
            <a class="rio-text-link" target="_blank" href="https://discord.gg/7ejXaPwhyH">Ask on Rio's Discord</a>
            <a class="rio-text-link" target="_blank" href="https://chatgpt.com">Ask ChatGPT</a>
            <a class="rio-text-link" target="_blank" href="https://rio.dev/docs?s=bf2">Read the docs</a>
        </div>
    </div>
</div>
"""


def make_error_message_component(
    err: t.Union[str, BaseException],
    project_directory: Path,
) -> rio.Component:
    html = make_traceback_html(
        err=err,
        project_directory=project_directory,
    )

    return rio.Html(
        html,
        align_x=0.5,
        align_y=0.2,
    )


def make_error_message_app(
    err: t.Union[str, BaseException],
    project_directory: Path,
    theme: rio.Theme | tuple[rio.Theme, rio.Theme],
) -> rio.App:
    """
    Creates an app that displays the given error message.
    """
    return rio.App(
        build=functools.partial(
            make_error_message_component, err, project_directory
        ),
        theme=theme,
    )


def modules_in_directory(project_path: Path) -> t.Iterable[str]:
    """
    Returns all currently loaded modules that reside in the given directory (or
    any subdirectory thereof). As a second condition, modules located inside of
    a virtual environment are not returned.

    The purpose of this is to yield all modules that belong to the user's
    project. This is the set of modules that makes sense to reload when the user
    makes a change.
    """
    # Resolve the path to avoid issues with symlinks
    project_path = project_path.resolve()

    # Paths known to be virtual environments, or not. All contained paths are
    # absolute.
    #
    # This acts as a cache to avoid hammering the filesystem.
    virtual_environment_paths: dict[Path, bool] = {}

    def is_virtualenv_dir(path: Path) -> bool:
        # Resolve the path to make sure we're dealing in absolutes and to avoid
        # issues with symlinks
        path = path.resolve()

        # Cached?
        try:
            return virtual_environment_paths[path]
        except KeyError:
            pass

        # Nope. Is this a venv?
        result = (path / "pyvenv.cfg").exists()

        # Cache & return
        virtual_environment_paths[path] = result
        return result

    # Walk all modules
    for name, module in list(sys.modules.items()):
        # Special case: Unloading Rio, while Rio is running is not that smart.
        if name == "rio" or name.startswith("rio."):
            continue

        # Where does the module live?
        try:
            module_path = getattr(module, "__file__", None)
        except AttributeError:
            continue

        try:
            module_path = Path(module_path).resolve()  # type: ignore
        except TypeError:
            continue

        # If the module isn't inside of the project directory, skip it
        if not module_path.is_relative_to(project_path):
            continue

        # Check all parent directories for virtual environments, up to the
        # project directory
        for parent in module_path.parents:
            # If we've reached the project directory, stop
            if parent == project_path:
                yield name
                break

            # If this is a virtual environment, skip the module
            if is_virtualenv_dir(parent):
                break


def import_app_module(
    proj: project_config.RioProjectConfig,
) -> types.ModuleType:
    """
    Python's importing is bizarre. This function tries to hide all of that and
    imports the module, as specified by the user. This can raise a variety of
    exceptions, since the module's code is evaluated.

    The module will be freshly imported, even if it was already imported before.
    """
    # Purge all modules that belong to the project. While the main module name
    # is known, deleting only that isn't enough in all projects. In complex
    # project structures it can be useful to have the UI code live in a module
    # that is then just loaded into a top-level Python file.
    for module_name in modules_in_directory(proj.project_directory):
        del sys.modules[module_name]

    # Inject the module path into `sys.path`. We add it at the start so that it
    # takes priority over all other modules. (Example: If someone names their
    # project "test", we don't end up importing python's builtin `test` module
    # on accident.)
    main_module_path = str(proj.app_main_module_path.parent)
    sys.path.insert(0, main_module_path)

    # Now (re-)import the app module. There is no need to import all the other
    # modules here, since they'll be re-imported as needed by the app module.
    try:
        return importlib.import_module(proj.app_main_module)

    # Finally, clean up `sys.path` again
    finally:
        sys.path.remove(main_module_path)


def load_user_app(
    proj: project_config.RioProjectConfig,
) -> tuple[
    rio.App,
    rio.app_server.fastapi_server.FastapiServer | None,
]:
    """
    Load and return the user app. Raises `AppLoadError` if the app can't be
    loaded for whichever reason.
    """
    # Import the app module
    try:
        app_module = import_app_module(proj)
    except BaseException as err:
        revel.error(f"Could not import `{proj.app_main_module}`:")

        revel.print(
            nice_traceback.format_exception_revel(
                err,
                relpath=proj.project_directory,
                frame_filter=traceback_frame_filter,
            )
        )

        raise AppLoadError() from err

    # Find the variable holding the Rio app.
    #
    # There are two cases here. Typically, there will be an instance of
    # `rio.App` somewhere. However, in order for users to be able to add custom
    # routes, there might also be a variable storing a `fastapi.FastAPI`, or, in
    # our case, an Rio's subclass thereof. If that is present, prefer it over
    # the plain Rio app.
    as_fastapi_apps: list[
        tuple[str, rio.app_server.fastapi_server.FastapiServer]
    ] = []
    rio_apps: list[tuple[str, rio.App]] = []

    for var_name, var in app_module.__dict__.items():
        if isinstance(var, rio.app_server.fastapi_server.FastapiServer):
            as_fastapi_apps.append((var_name, var))

        if isinstance(var, rio.App):
            rio_apps.append((var_name, var))

    # Prepare the main file name
    if app_module.__file__ is None:
        main_file_reference = f"Your app's main file"
    else:
        main_file_reference = f"The file `{Path(app_module.__file__).relative_to(proj.project_directory)}`"

    # Which type of app do we have?
    #
    # Case: FastAPI app
    if len(as_fastapi_apps) > 1:
        app_list = as_fastapi_apps
        app_server = as_fastapi_apps[0][1]
        app_instance = app_server.app
    # Case: Rio app
    elif len(rio_apps) > 0:
        app_list = rio_apps
        app_server = None
        app_instance = rio_apps[0][1]
    # Case: No app
    else:
        raise AppLoadError(
            f"Cannot find your app. {main_file_reference} needs to to define a"
            f" variable that is a Rio app. Something like `app = rio.App(...)`"
        )

    # Make sure there was only one app to choose from, within the chosen
    # category
    if len(app_list) > 1:
        variables_string = (
            "`" + "`, `".join(var_name for var_name, _ in app_list) + "`"
        )
        raise AppLoadError(
            f"{main_file_reference} defines multiple Rio apps: {variables_string}. Please make sure there is exactly one."
        )

    # Explicitly set the project location because it can't reliably be
    # auto-detected. This also affects the assets_dir and the implicit page
    # loading.
    try:
        app_instance._main_file = proj.app_main_module_path
    except FileNotFoundError as error:
        raise AppLoadError(str(error))

    app_instance._compute_assets_dir()

    app_instance._load_pages()
    app_instance._raw_pages = (
        app_instance.pages
    )  # Prevent auto_detect_pages() from running twice

    return app_instance, app_server
