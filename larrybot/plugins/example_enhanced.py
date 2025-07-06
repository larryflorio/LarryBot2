"""
Example enhanced plugin demonstrating the new architectural features.
This plugin shows how to use decorators, service layer, and dependency injection.
"""
from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry, CommandMetadata
from larrybot.core.event_bus import EventBus
from larrybot.core.interfaces import PluginInterface
from larrybot.utils.decorators import command_handler, event_listener, require_args, validate_user_id
from larrybot.services.base_service import BaseService
from larrybot.core.dependency_injection import ServiceLocator
from larrybot.core.event_utils import safe_event_handler
from typing import Dict, Any


class ExampleService(BaseService):
    """Example service demonstrating business logic separation."""

    async def execute(self, operation: str, data: Dict[str, Any]) ->Dict[
        str, Any]:
        """Execute example operations."""
        try:
            if operation == 'process_data':
                return self._create_success_response({'processed': data.get
                    ('input', '').upper()}, 'Data processed successfully')
            elif operation == 'calculate':
                numbers = data.get('numbers', [])
                result = sum(numbers)
                return self._create_success_response({'sum': result,
                    'count': len(numbers)},
                    f'Calculated sum of {len(numbers)} numbers')
            else:
                return self._handle_error(ValueError(
                    f'Unknown operation: {operation}'))
        except Exception as e:
            return self._handle_error(e, f'Error in {operation}')


example_service = ExampleService()


@command_handler(command='/example', description=
    'Example command demonstrating new features', usage=
    '/example <operation> [data]', category='examples')
@require_args(1, 2)
async def example_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Example command handler using decorators."""
    operation = context.args[0]
    data = context.args[1] if len(context.args) > 1 else ''
    result = await example_service.execute(operation, {'input': data})
    if result['success']:
        await update.message.reply_text(
            f"✅ {result['message']}\n{result['data']}")
    else:
        await update.message.reply_text(f"❌ Error: {result['error']}")


@command_handler(command='/calculate', description=
    'Calculate sum of numbers', usage='/calculate <num1> <num2> [num3...]',
    category='examples')
@require_args(2)
async def calculate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Calculate sum of provided numbers."""
    try:
        numbers = [float(arg) for arg in context.args]
        result = await example_service.execute('calculate', {'numbers':
            numbers})
        if result['success']:
            await update.message.reply_text(
                f"""📊 Calculation Result:
Sum: {result['data']['sum']}
Numbers processed: {result['data']['count']}"""
                )
        else:
            await update.message.reply_text(f"❌ Error: {result['error']}")
    except ValueError:
        await update.message.reply_text('❌ Please provide valid numbers')


@command_handler(command='/help_examples', description=
    'Show help for example commands', usage='/help_examples', category=
    'examples')
async def help_examples_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Show help for example commands."""
    help_text = """
🤖 **Example Commands Help**

**Basic Example:**
`/example process_data hello world`
- Processes text data

**Calculation:**
`/calculate 1 2 3 4 5`
- Calculates sum of numbers

**Help:**
`/help_examples`
- Shows this help message

**Features Demonstrated:**
✅ Command decorators with metadata
✅ Argument validation
✅ Service layer separation
✅ Error handling
✅ Event-driven architecture
✅ Safe event handling
"""
    await update.message.reply_text(help_text)


@event_listener('task_created')
@safe_event_handler
def handle_task_created(task):
    """Example event listener for task creation."""
    print(f'🎉 New task created: {task.description} (ID: {task.id})')


@event_listener('task_completed')
@safe_event_handler
def handle_task_completed(task):
    """Example event listener for task completion."""
    print(f'✅ Task completed: {task.description} (ID: {task.id})')


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """
    Register the example plugin with the system.
    Demonstrates enhanced registration with metadata.
    """
    command_registry.register('/example', example_handler, CommandMetadata(
        name='/example', description=
        'Example command demonstrating new features', usage=
        '/example <operation> [data]', category='examples'))
    command_registry.register('/calculate', calculate_handler,
        CommandMetadata(name='/calculate', description=
        'Calculate sum of numbers', usage=
        '/calculate <num1> <num2> [num3...]', category='examples'))
    command_registry.register('/help_examples', help_examples_handler,
        CommandMetadata(name='/help_examples', description=
        'Show help for example commands', usage='/help_examples', category=
        'examples'))
    event_bus.subscribe('task_created', handle_task_created)
    event_bus.subscribe('task_completed', handle_task_completed)
    print('📦 Example enhanced plugin registered successfully!')


PLUGIN_METADATA = {'name': 'example_enhanced', 'version': '1.0.0',
    'description':
    'Example plugin demonstrating enhanced architectural features',
    'author': 'LarryBot Team', 'dependencies': ['event_bus',
    'command_registry'], 'enabled': True}
