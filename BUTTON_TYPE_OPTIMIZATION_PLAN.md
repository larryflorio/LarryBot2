# ButtonType Optimization Plan

## 🎯 **Current State Analysis**

### ✅ **Correctly Assigned (Keep as-is):**
- **Delete/Remove actions** → `ButtonType.DANGER` 
- **Complete/Success actions** → `ButtonType.SUCCESS`
- **Primary actions** → `ButtonType.PRIMARY`
- **Navigation/Back** → `ButtonType.SECONDARY`
- **Cancel actions** → `ButtonType.DANGER`

### 🔧 **Optimization Opportunities:**

#### **1. View/Info Buttons**
- **Current**: `ButtonType.INFO`
- **Proposed**: `ButtonType.INFO` (keep as-is)
- **Rationale**: Info buttons should remain INFO for consistency

#### **2. Edit Buttons**
- **Current**: `ButtonType.PRIMARY` 
- **Proposed**: `ButtonType.INFO`
- **Rationale**: Edit is informational/actionable, not primary action

#### **3. Refresh Buttons**
- **Current**: `ButtonType.SECONDARY`
- **Proposed**: `ButtonType.INFO`
- **Rationale**: Refresh is informational, not secondary action

#### **4. Analytics Buttons**
- **Current**: `ButtonType.INFO`
- **Proposed**: `ButtonType.INFO` (keep as-is)
- **Rationale**: Analytics are informational

## 🚀 **Implementation Plan**

### **Phase 1: Edit Button Optimization**
- Change edit buttons from `ButtonType.PRIMARY` to `ButtonType.INFO`
- Files affected: `tasks.py`, `client.py`

### **Phase 2: Refresh Button Optimization**
- Change refresh buttons from `ButtonType.SECONDARY` to `ButtonType.INFO`
- Files affected: `calendar.py`, `performance.py`

### **Phase 3: Validation**
- Run tests to ensure no regressions
- Manual UI testing for button appearance

## 📋 **ButtonType Semantic Guidelines**

### **ButtonType.PRIMARY**
- Main actions (Add, Create, Confirm, Save)
- Primary navigation (Main Menu, Home)
- Critical user flows

### **ButtonType.SECONDARY**
- Navigation (Back, Cancel, Skip)
- Secondary actions
- Alternative options

### **ButtonType.SUCCESS**
- Complete actions (Done, Finish, Complete)
- Positive confirmations
- Success states

### **ButtonType.DANGER**
- Destructive actions (Delete, Remove, Cancel)
- Warning states
- High-risk operations

### **ButtonType.WARNING**
- Caution states
- Attention-required actions
- Medium-risk operations

### **ButtonType.INFO**
- Informational actions (View, Edit, Refresh, Analytics)
- Data display actions
- Non-destructive operations 