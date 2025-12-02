# enums/file_action.py


import enum


class FileAction(str, enum.Enum):
    """This enumeration specifies the actions that can be performed when a file or directory already exists.

    The available actions include:

    - **ARCHIVE**: Move the existing file to an archive location before writing a new one.
    - **ASK**: Prompt the user to select an action.
    - **DELETE**: Permanently remove the existing file without archiving.
    - **OVERWRITE**: Replace the existing file with a new one.
    - **SKIP**: Do not perform any action if the file exists.

    The `FileManager` class utilizes this enumeration to determine the appropriate
    action to take. The default action is `ASK`.

    **Attributes:**
        FileAction (enum.Enum): Enumeration of available file actions.

    **Examples:**

    Examples:
        ```python
        from coregen.cli.enums.enum_file_action import FileAction

        action = FileAction.ARCHIVE
        printf("archive is: {action})
        # Output: archive is: archive
        ```
    """

    ASK = "ask"  # Ask user for action
    SKIP = "skip"  # Skip if file exists
    OVERWRITE = "overwrite"  # Overwrite existing file
    ARCHIVE = "archive"  # Archive existing file before writing
    DELETE = "delete"  # Delete existing file without archiving
