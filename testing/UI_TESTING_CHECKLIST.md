# UI Testing Checklist for Bulk Rubric Generation

## 🚀 Pre-Testing Setup

- [ ] Start the server: `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- [ ] Open browser and navigate to `http://localhost:8000`
- [ ] Ensure you have at least one assignment with questions in the database

## 🧪 Manual Testing Steps

### 1. **Basic UI Loading**

- [ ] Page loads without JavaScript errors
- [ ] Assignments tab is visible and accessible
- [ ] Assignment list displays correctly
- [ ] No console errors in browser developer tools

### 2. **Assignment Display**

- [ ] Assignments show correct title, question count, and marks
- [ ] Assignment accordions expand/collapse properly
- [ ] Questions are displayed with correct formatting
- [ ] Question type badges are visible
- [ ] Marks badges are visible

### 3. **Rubric Status Indicators**

- [ ] Questions without rubrics show "❌ No Rubric" badge
- [ ] Questions with rubrics show "✅ Rubric Available" badge
- [ ] Rubric status badges have correct colors (red for missing, green for available)

### 4. **Button States**

- [ ] "Build Rubrics" button is visible for assignments without rubrics
- [ ] "Rebuild Rubrics" button is visible for assignments with existing rubrics
- [ ] Button text changes based on rubric status

### 5. **Bulk Rubric Generation**

- [ ] Click "Build Rubrics" button
- [ ] Button shows "Building Rubrics..." loading state
- [ ] Button is disabled during processing
- [ ] Success notification appears after completion
- [ ] Notification shows correct counts (processed/total questions)
- [ ] Assignment list refreshes automatically
- [ ] Rubric status badges update to show "✅ Rubric Available"

### 6. **Error Handling**

- [ ] Test with invalid assignment ID (should show error notification)
- [ ] Test network disconnection (should show appropriate error)
- [ ] Test server restart during processing (should show error)
- [ ] Error notifications are dismissible
- [ ] Button resets to original state after errors

### 7. **Notifications**

- [ ] Success notifications appear in top-right corner
- [ ] Error notifications appear in top-right corner
- [ ] Notifications have correct colors (green for success, red for error)
- [ ] Notifications auto-dismiss after 5 seconds
- [ ] Close button (×) works to dismiss notifications
- [ ] Multiple notifications stack properly

### 8. **Mobile Responsiveness**

- [ ] Test on mobile device or browser dev tools mobile view
- [ ] Notifications are properly sized for mobile
- [ ] Buttons are touch-friendly
- [ ] Text is readable on small screens

### 9. **Performance**

- [ ] Page loads quickly
- [ ] Button clicks are responsive
- [ ] No memory leaks (check browser dev tools)
- [ ] Large assignments don't cause UI freezing

### 10. **Edge Cases**

- [ ] Test with assignment that has no questions
- [ ] Test with assignment that has many questions (10+)
- [ ] Test rapid button clicks (should be prevented)
- [ ] Test browser refresh during processing
- [ ] Test browser back/forward navigation

## 🐛 Common Issues to Check

### **JavaScript Errors**

- [ ] No `TypeError` in console
- [ ] No `ReferenceError` in console
- [ ] No `SyntaxError` in console

### **CSS Issues**

- [ ] All styles load correctly
- [ ] No broken images or missing icons
- [ ] Colors are consistent with design
- [ ] Animations work smoothly

### **API Issues**

- [ ] Network requests complete successfully
- [ ] Response data is properly parsed
- [ ] Error responses are handled gracefully
- [ ] Timeout handling works correctly

## 📊 Testing Results

### **Pass/Fail Summary**

- [ ] All basic functionality tests pass
- [ ] All error handling tests pass
- [ ] All UI/UX tests pass
- [ ] All performance tests pass

### **Issues Found**

- [ ] List any issues discovered during testing
- [ ] Note severity (Critical, High, Medium, Low)
- [ ] Document steps to reproduce

### **Recommendations**

- [ ] Any improvements needed
- [ ] Performance optimizations
- [ ] UX enhancements

## 🎯 Success Criteria

The UI is ready for production if:

- [ ] All checklist items are checked
- [ ] No critical issues remain
- [ ] Performance is acceptable
- [ ] Error handling is robust
- [ ] User experience is smooth

---

**Tested by:** ********\_********  
**Date:** ********\_********  
**Version:** ********\_********
