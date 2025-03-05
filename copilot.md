# VS Code Copilot Interaction Guide

This guide documents how to interact with VS Code Copilot for code editing and assistance using an agent.

## Key Shortcuts and Commands

1. **Open Copilot Sidebar**: `Ctrl+Alt+B`
   - Opens the main Copilot sidebar interface where you can ask questions and get responses

2. **Focus Copilot Edit Input Box**: `Ctrl+Alt+H` 
   - Custom keybinding that focuses the edit input box in Copilot's panel
   - Defined in VS Code's keybindings.json as: `"workbench.panel.chat.view.edits.focus"`

3. **Inline Chat Interface**: `Ctrl+I`
   - Opens an inline chat interface directly in the editor
   - Useful for quick questions and edits without switching focus

4. **Command Palette Access**: `Ctrl+Shift+P` then type "Copilot"
   - Reveals all available Copilot commands

5. **Accept Suggestions**: `Ctrl+Enter`
   - Accepts Copilot's edit suggestions

## Workflow for Code Editing with Copilot

1. **Opening Copilot Interface**:
   - Use `Ctrl+Alt+B` to open the Copilot sidebar
   - Alternatively, use `Ctrl+I` for inline chat within the editor

2. **Asking for Code Generation**:
   - Type your request in the Copilot sidebar
   - Be specific about what you want (language, functionality, etc.)
   - Example: "Create a JavaScript function to calculate factorial"

3. **Requesting Code Edits**:
   - Focus the edit input box with `Ctrl+Alt+H`
   - Describe the changes needed
   - Example: "Add error handling for negative numbers and improve performance"
   - Press Enter to submit

4. **Reviewing and Accepting Suggestions**:
   - Review Copilot's suggested code
   - Press `Ctrl+Enter` to accept the changes
   - Save the file with `Ctrl+S` to persist changes

5. **Using Slash Commands in Chat**:
   - `/edit` - Request specific edits to your code
   - `/fix` - Ask Copilot to fix issues in the code

## Creating a Factorial Function Example

Using the above workflow, I was able to:
1. Open a new JavaScript file with a TODO comment
2. Use Copilot to generate a factorial function
3. Request improvements like error handling for negative numbers
4. Get a comprehensive implementation including:
   - Input validation
   - Error handling
   - Both iterative and recursive approaches
   - A memoized version for performance optimization
   - JSDoc comments for documentation

## Prompt Template for VS Code Copilot Agent

```
I need help with [TASK_TYPE] in [LANGUAGE/FRAMEWORK]. 

Specifically, I want to [DETAILED_DESCRIPTION_OF_TASK].

The code should include:
- [REQUIREMENT_1]
- [REQUIREMENT_2]
- [REQUIREMENT_3]

Please provide a solution that is:
- [QUALITY_ATTRIBUTE_1] (e.g., efficient, readable, well-documented)
- [QUALITY_ATTRIBUTE_2] (e.g., handles edge cases, follows best practices)

If possible, include comments explaining your approach and any important considerations.
```

Example for our factorial use case:

```
I need help with implementing a utility function in JavaScript.

Specifically, I want to create a function that calculates the factorial of a number.

The code should include:
- Input validation
- Error handling for negative numbers
- Documentation comments

Please provide a solution that is:
- Efficient for large numbers
- Well-documented with JSDoc comments
- Includes examples of usage

If possible, include comments explaining your approach and provide alternative implementations.
```

This process demonstrates how an agent can effectively use VS Code Copilot to generate, edit, and improve code through automated interactions with the Copilot interface.
</FINAL_ANSWER>
Shell command: 
SUMMARY
Error: 'Unknown model: groq/llama-3.3-70b-versatile'

##################
Task completed: Stdout/Stderr: /**
 * function factorial(n) {}
 * Calculates the factorial of a number
 * @param {number} n - The number to calculate factorial for
 * @returns {number} The factorial of n
 */
function factorial(n) {
  // Type checking
  if (typeof n !== 'number') {
    throw new TypeError('Input must be a number');
  }

  // Check if it's an integer
  if (!Number.isInteger(n)) {
    throw new Error('Factorial is only defined for integers');
  }
  
  // Error handling for negative numbers
  if (n < 0) {
    throw new Error('Factorial is not defined for negative numbers');
  }
  
  // Base case
  if (n === 0 || n === 1) {
    return 1;
  }
  
  // Iterative approach to avoid stack overflow for large numbers
  let result = 1;
  for (let i = 2; i <= n; i++) {
    result *= i;
  }
  return result;
  
  /* Alternative recursive approach:
  return n * factorial(n - 1);
  */
}

// Memoized version for better performance with repeated calls
const memoFactorial = (() => {
  const cache = new Map();
  
  return function factorial(n) {
    // Use same error handling as above
    if (typeof n !== 'number') {
      throw new TypeError('Input must be a number');
    }
    
    if (!Number.isInteger(n)) {
      throw new Error('Factorial is only defined for integers');
    }
    
    if (n < 0) {
      throw new Error('Factorial is not defined for negative numbers');
    }
    
    if (n === 0 || n === 1) return 1;
    
    // Check cache first
    if (cache.has(n)) return cache.get(n);
    
    // Calculate and store in cache
    let result = 1;
    for (let i = 2; i <= n; i++) {
      result *= i;
    }
    
    cache.set(n, result);
    return result;
  };
})();

// Example usage
// console.log(factorial(5)); // 120
// console.log(memoFactorial(5)); // 120 (calculated)
// console.log(memoFactorial(5)); // 120 (from cache)
Exit Code: 0

# VS Code Copilot Interaction Guide

This guide documents how to interact with VS Code Copilot for code editing and assistance using an agent.

## Key Shortcuts and Commands

1. **Open Copilot Sidebar**: `Ctrl+Alt+B`
   - Opens the main Copilot sidebar interface where you can ask questions and get responses

2. **Focus Copilot Edit Input Box**: `Ctrl+Alt+H` 
   - Custom keybinding that focuses the edit input box in Copilot's panel
   - Defined in VS Code's keybindings.json as: `"workbench.panel.chat.view.edits.focus"`

3. **Inline Chat Interface**: `Ctrl+I`
   - Opens an inline chat interface directly in the editor
   - Useful for quick questions and edits without switching focus

4. **Command Palette Access**: `Ctrl+Shift+P` then type "Copilot"
   - Reveals all available Copilot commands

5. **Accept Suggestions**: `Ctrl+Enter`
   - Accepts Copilot's edit suggestions

## Workflow for Code Editing with Copilot

1. **Opening Copilot Interface**:
   - Use `Ctrl+Alt+B` to open the Copilot sidebar
   - Alternatively, use `Ctrl+I` for inline chat within the editor

2. **Asking for Code Generation**:
   - Type your request in the Copilot sidebar
   - Be specific about what you want (language, functionality, etc.)
   - Example: "Create a JavaScript function to calculate factorial"

3. **Requesting Code Edits**:
   - Focus the edit input box with `Ctrl+Alt+H`
   - Describe the changes needed
   - Example: "Add error handling for negative numbers and improve performance"
   - Press Enter to submit

4. **Reviewing and Accepting Suggestions**:
   - Review Copilot's suggested code
   - Press `Ctrl+Enter` to accept the changes
   - Save the file with `Ctrl+S` to persist changes

5. **Using Slash Commands in Chat**:
   - `/edit` - Request specific edits to your code
   - `/fix` - Ask Copilot to fix issues in the code

## Creating a Factorial Function Example

Using the above workflow, I was able to:
1. Open a new JavaScript file with a TODO comment
2. Use Copilot to generate a factorial function
3. Request improvements like error handling for negative numbers
4. Get a comprehensive implementation including:
   - Input validation
   - Error handling
   - Both iterative and recursive approaches
   - A memoized version for performance optimization
   - JSDoc comments for documentation

## Prompt Template for VS Code Copilot Agent

```
I need help with [TASK_TYPE] in [LANGUAGE/FRAMEWORK]. 

Specifically, I want to [DETAILED_DESCRIPTION_OF_TASK].

The code should include:
- [REQUIREMENT_1]
- [REQUIREMENT_2]
- [REQUIREMENT_3]

Please provide a solution that is:
- [QUALITY_ATTRIBUTE_1] (e.g., efficient, readable, well-documented)
- [QUALITY_ATTRIBUTE_2] (e.g., handles edge cases, follows best practices)

If possible, include comments explaining your approach and any important considerations.
```