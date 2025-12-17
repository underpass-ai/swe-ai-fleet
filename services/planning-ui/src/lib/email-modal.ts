/**
 * Email Modal Utility
 * Provides a reusable modal for collecting email input from users
 */

interface ModalConfig {
  title: string;
  placeholder: string;
  inputType: 'email' | 'text';
  required: boolean;
  labelText?: string;
  helpText?: string;
}

function createModalHandler(config: ModalConfig): Promise<string | null> {
  return new Promise((resolve) => {
    const modal = document.getElementById('email-modal');
    const backdrop = document.getElementById('email-modal-backdrop');
    const input = document.getElementById('email-input') as HTMLInputElement;
    const titleEl = document.getElementById('email-modal-title');
    const labelEl = document.getElementById('email-modal-label');
    const helpEl = document.getElementById('email-modal-help');
    const submitBtn = document.getElementById('email-modal-submit');
    const cancelBtn = document.getElementById('email-modal-cancel');

    if (!modal || !input || !submitBtn || !cancelBtn) {
      resolve(null);
      return;
    }

    // Update title
    if (titleEl) {
      titleEl.textContent = config.title;
    }

    // Update label
    if (labelEl) {
      labelEl.textContent = config.labelText || (config.inputType === 'email' ? 'Email Address' : 'Input');
    }

    // Update help text
    if (helpEl) {
      helpEl.textContent = config.helpText ||
        (config.required
          ? 'This field is required.'
          : 'Press Cancel to skip this step.');
    }

    // Configure input
    input.type = config.inputType;
    input.placeholder = config.placeholder;
    input.value = '';
    input.required = config.required;

    // Show modal
    modal.classList.remove('hidden');
    input.focus();

    // Cleanup function
    const cleanup = () => {
      modal.classList.add('hidden');
      input.type = 'email'; // Reset to email type
      if (labelEl) labelEl.textContent = 'Email Address';
      if (helpEl) helpEl.textContent = 'Please enter your email address to continue.';
      submitBtn.removeEventListener('click', handleSubmit);
      cancelBtn.removeEventListener('click', handleCancel);
      backdrop?.removeEventListener('click', handleCancel);
      input.removeEventListener('keydown', handleKeyDown);
    };

    // Submit handler
    const handleSubmit = () => {
      const value = input.value.trim();
      const isValid = config.inputType === 'email'
        ? (value && input.validity.valid)
        : (value || !config.required);

      if (isValid) {
        cleanup();
        resolve(value || null);
      } else {
        input.reportValidity();
      }
    };

    // Cancel handler
    const handleCancel = () => {
      cleanup();
      resolve(null);
    };

    // Enter key handler
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleSubmit();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        handleCancel();
      }
    };

    // Attach event listeners
    submitBtn.addEventListener('click', handleSubmit);
    cancelBtn.addEventListener('click', handleCancel);
    backdrop?.addEventListener('click', handleCancel);
    input.addEventListener('keydown', handleKeyDown);
  });
}

export function showEmailModal(
  title: string = 'Product Owner Email',
  placeholder: string = 'your.email@example.com'
): Promise<string | null> {
  return createModalHandler({
    title,
    placeholder,
    inputType: 'email',
    required: true,
    helpText: 'Please enter your email address to continue.',
  });
}

/**
 * Text Input Modal (for non-email inputs like notes, reasons, etc.)
 */
export function showTextModal(
  title: string,
  placeholder: string = 'Enter text...',
  required: boolean = false
): Promise<string | null> {
  return createModalHandler({
    title,
    placeholder,
    inputType: 'text',
    required,
    labelText: title.includes('email') ? 'Email Address' : 'Input',
    helpText: required
      ? 'This field is required.'
      : 'Press Cancel to skip this step.',
  });
}



