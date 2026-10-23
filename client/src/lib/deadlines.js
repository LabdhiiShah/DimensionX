// src/lib/deadlines.js

/**
 * Returns an array of projects that are due within the next 7 days, 
 * or are already overdue.
 */
export function getUrgentProjects(projects) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return projects.filter((p) => {
    // Ignore completed projects!
    if (p.status === 'completed') return false;
    if (!p.dueDate) return false;
    
    const due = new Date(p.dueDate);
    due.setHours(0, 0, 0, 0);
    
    const diffDays = Math.ceil((due - today) / (1000 * 60 * 60 * 24));
    return diffDays <= 7;
  });
}

/**
 * Returns the status text and color for a given due date.
 */
export function getDeadlineStatus(dueDate) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const due = new Date(dueDate);
  due.setHours(0, 0, 0, 0);
  
  const diffDays = Math.ceil((due - today) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) {
    return { text: `Overdue by ${Math.abs(diffDays)} day(s)`, color: '#d9534f' };
  }
  if (diffDays === 0) {
    return { text: 'Due Today', color: '#f0ad4e' };
  }
  return { text: `Due in ${diffDays} day(s)`, color: '#5bc0de' };
}

/**
 * Checks if a project is already past its due date.
 */
export function isOverdue(dueDate) {
  if (!dueDate) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return new Date(dueDate) < today;
}