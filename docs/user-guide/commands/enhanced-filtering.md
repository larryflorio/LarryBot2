---
title: Enhanced Filtering and Search
description: Unified search capabilities with basic and advanced modes
last_updated: 2025-07-01
---

# Enhanced Filtering and Search 🔍

> **🆕 New in v2.1.6:** Search commands consolidated into unified `/search` with flag-based modes! Enhanced `/search` now provides both basic and advanced functionality through intelligent parameter handling.

LarryBot2's **unified search system** provides powerful tools for finding and organizing tasks efficiently through a single enhanced command that adapts to your needs. The enhanced search supports both simple queries and advanced features through optional flags.

## 🎯 Overview

The enhanced search system enables you to:
- Search across task descriptions, comments, and tags with unified interface
- Use basic search for quick queries or advanced search for complex needs
- Apply case-sensitive matching when precision is required
- Filter by multiple criteria simultaneously with other filter commands
- Sort results by various fields and combine with time ranges

## 📋 **Enhanced Search Command**

### `/search` - **Unified Search** ⭐
**Enhanced**: Now supports both basic AND advanced search modes through flag-based parameters.

**Usage**:
- **Basic**: `/search <query>` (simple text search)
- **Advanced**: `/search <query> --advanced` (enhanced search features)
- **Case-Sensitive**: `/search <query> --case-sensitive` (exact case matching)
- **Full Advanced**: `/search <query> --advanced --case-sensitive` (all features)

**Progressive Enhancement**: Start with simple search, add flags for advanced features.

#### **Basic Search** (default)
```bash
/search authentication
/search "API documentation"  
/search bugfix
/search "client meeting"
```

**Parameters**:
- `query` (required): Text to search for (supports phrases in quotes)

#### **Advanced Search** (enhanced features)
```bash
/search authentication --advanced
/search "API documentation" --advanced  
/search Authentication --case-sensitive
/search "API Documentation" --advanced --case-sensitive
```

**Enhanced Parameters**:
- `--advanced`: Enable advanced search features (tag search, comment search, fuzzy matching)
- `--case-sensitive`: Enable case-sensitive matching for exact precision

**Response**:
```
🔍 **Advanced Search Results for 'authentication'** (2 found)

1. 🔴 **Fix authentication bug** (ID: 128)
   📝 Todo | High | Development

2. 🟡 **Update authentication module** (ID: 129)
   📝 In Progress | Medium | Development

[Inline keyboard: Filter | Sort | Export]
```

### `/filter_advanced` - Advanced Filtering
Filter tasks with multiple criteria and sorting options.

**Usage**: `/filter_advanced [status] [priority] [category] [sort_by] [sort_order]`

**Parameters**:
- `status` (optional): Todo, In Progress, Review, Done
- `priority` (optional): Low, Medium, High, Critical
- `category` (optional): Any category name
- `sort_by` (optional): created_at, due_date, priority, status, category
- `sort_order` (optional): asc, desc

**Examples**:
```
/filter_advanced Todo High Development
/filter_advanced In Progress Medium Testing created_at desc
/filter_advanced Review priority asc
/filter_advanced High created_at desc
```

**Response**:
```
📊 **Advanced Filter Results** (2 found)

1. 🔴 **Fix authentication bug** (ID: 128)
   📝 Todo | High | Development

2. 🔴 **Update authentication module** (ID: 129)
   📝 Todo | High | Development

[Inline keyboard: Filter | Sort | Export]
```

### `/tags_multi` - Multi-Tag Filtering
Filter tasks by multiple tags with "all" or "any" matching logic.

**Usage**: `/tags_multi <tag1,tag2,tag3> [all|any]`

**Parameters**:
- `tags`: Comma-separated list of tags
- `match_all` (optional): "all" (default) or "any"

**Examples**:
```
/tags_multi urgent,bug all
/tags_multi feature,enhancement any
/tags_multi bug,fix,urgent all
/tags_multi documentation,api any
```

**Response**:
```
🏷️ **Tasks matching all of tags: urgent, bug** (1 found)

1. 🔴 **Fix authentication bug** (ID: 128)
   📝 Todo | High | Development
   🏷️ Tags: urgent, bug, fix

[Inline keyboard: Filter | Sort | Export]
```

### `/time_range` - Time Range Filtering
Filter tasks by creation or due dates within a specific range.

**Usage**: `/time_range <start_date> <end_date> [include_completed]`

**Parameters**:
- `start_date`: Start date in YYYY-MM-DD format
- `end_date`: End date in YYYY-MM-DD format
- `include_completed` (optional): true/false (default: false)

**Examples**:
```
/time_range 2025-07-01 2025-07-31
/time_range 2025-07-01 2025-07-31 true
/time_range 2025-06-01 2025-06-30
```

**Response**:
```
📅 **Tasks in time range 2025-07-01 to 2025-07-31** (including completed) (3 found)

1. 🔴 **Complete project proposal** (ID: 124)
   ⏰ Due: 2025-07-05
   📝 Todo | High

2. ✅ **Call client about project** (ID: 125)
   ⏰ Due: 2025-07-10
   📝 Done | Medium

3. 🟡 **Write unit tests** (ID: 127)
   ⏰ Due: 2025-07-15
   📝 Todo | Medium

[Inline keyboard: Filter | Sort | Export]
```

### `/priority_range` - Priority Range Filtering
Filter tasks within a priority range.

**Usage**: `/priority_range <min_priority> <max_priority>`

**Parameters**:
- `min_priority`: Minimum priority (Low, Medium, High, Critical)
- `max_priority`: Maximum priority (Low, Medium, High, Critical)

**Examples**:
```
/priority_range Medium High
/priority_range Low Critical
/priority_range High Critical
```

**Response**:
```
🎯 **Tasks in priority range Medium to High** (2 found)

1. 🔴 **Complete project proposal** (ID: 124)
   📝 Todo | High | work

2. 🟡 **Write unit tests** (ID: 127)
   📝 Todo | Medium | development

[Inline keyboard: Filter | Sort | Export]
```

---

## 🧑‍💻 Best Practices & Tips
- All commands provide actionable, visually distinct feedback using MarkdownV2 and emoji.
- Use inline keyboards for navigation, filtering, and sorting options.
- Error messages include suggestions and are easy to spot.
- Progressive disclosure: Only see advanced options when needed.
- All flows are mobile-friendly and accessible.
- Combine filters for precise results.

---

For advanced features, see [Task Management](task-management.md), [Bulk Operations](bulk-operations.md), and [Analytics Reporting](analytics-reporting.md).

## 🎯 Best Practices

### Search Strategies
1. **Use specific terms**: Be specific in your search terms
2. **Try different variations**: Use synonyms or related terms
3. **Use quotes for phrases**: Enclose exact phrases in quotes
4. **Combine with filters**: Use search with other filters

### Filtering Strategies
1. **Start broad**: Begin with basic filters and narrow down
2. **Use multiple criteria**: Combine status, priority, and category
3. **Sort results**: Use sorting to organize results logically
4. **Save common filters**: Note useful filter combinations

### Tag Management
1. **Consistent naming**: Use consistent tag names across tasks
2. **Hierarchical tags**: Use parent-child tag relationships
3. **Regular cleanup**: Remove unused tags periodically
4. **Document conventions**: Maintain tag naming conventions

### Time Management
1. **Use date ranges**: Filter by relevant time periods
2. **Include completed tasks**: Review completed work for patterns
3. **Plan ahead**: Use future date ranges for planning
4. **Track trends**: Use time ranges to identify trends

## 📊 Common Use Cases

### Project Management
```
# Find all high-priority development tasks
/filter_advanced Todo High Development

# Search for specific project features
/search_advanced "user authentication"

# Find tasks due this month
/time_range 2025-07-01 2025-07-31
```

### Bug Tracking
```
# Find all bug-related tasks
/tags_multi bug,fix all

# Search for specific bug types
/search_advanced "authentication bug"

# Find urgent bugs
/filter_advanced Todo Critical
/tags_multi urgent,bug all
```

### Client Work
```
# Find all client-related tasks
/search_advanced "client"

# Filter by client category
/filter_advanced In Progress Medium client

# Find overdue client tasks
/overdue
/filter_advanced Todo High client
```

### Documentation
```
# Find documentation tasks
/search_advanced "documentation"

# Find API-related tasks
/tags_multi api,documentation any

# Find tasks needing documentation
/filter_advanced Todo Medium
/search_advanced "needs docs"
```

## 🔍 Advanced Techniques

### Combining Filters
```
# High-priority bugs in development
/filter_advanced Todo High Development
/tags_multi bug,urgent all

# Client tasks due this week
/time_range 2025-07-01 2025-07-07
/search_advanced "client"
```

### Search Patterns
```
# Find tasks with specific patterns
/search_advanced "TODO:"
/search_advanced "FIXME:"
/search_advanced "BUG:"

# Find tasks by file type
/search_advanced ".py"
/search_advanced ".js"
/search_advanced ".md"
```

### Time-Based Analysis
```
# Tasks created this month
/time_range 2025-07-01 2025-07-31 true

# Overdue tasks by priority
/overdue
/priority_range High Critical

# Recent activity
/time_range 2025-06-20 2025-06-28 true
```

## ⚠️ Performance Considerations

### Large Datasets
- Advanced filtering is optimized for large task collections
- Recommended limit: 1000+ tasks
- Results are limited to prevent performance issues

### Search Performance
- Full-text search uses database indexing
- Complex searches may take longer
- Use specific terms for faster results

### Filter Combinations
- Multiple filters are processed efficiently
- Complex combinations may affect performance
- Consider breaking complex queries into simpler ones

## 🔍 Troubleshooting

### Common Issues

**No Results Found**
```
🔍 No tasks found matching your criteria
```
*Solutions*:
- Try broader search terms
- Check spelling and case
- Use fewer filter criteria
- Verify tag names

**Too Many Results**
```
📊 Found 150+ tasks (showing first 50)
```
*Solutions*:
- Add more specific filters
- Use more specific search terms
- Combine multiple criteria
- Use time ranges to limit scope

**Invalid Parameters**
```
❌ Invalid sort field: 'invalid_field'
❌ Invalid priority: 'invalid_priority'
```
*Solutions*:
- Check parameter spelling
- Use correct parameter values
- Review command syntax
- Consult parameter documentation

### Error Recovery
1. **Simplify Query**: Start with basic filters
2. **Check Syntax**: Verify command format
3. **Use Examples**: Reference working examples
4. **Test Incrementally**: Add filters one by one

## 📈 Analytics Integration

### Search Analytics
- Search patterns are tracked for insights
- Popular search terms are identified
- Filter usage is analyzed for optimization

### Performance Metrics
- Search response times are monitored
- Filter efficiency is measured
- User behavior patterns are analyzed

### Continuous Improvement
- Search algorithms are refined based on usage
- Filter options are expanded based on needs
- Performance is optimized based on metrics

## 🔄 Recent Updates (June 28, 2025)

### Week 2 Implementation
- **Repository Layer**: Enhanced with advanced filtering methods
- **Service Layer**: Added comprehensive search and filter logic
- **Command Handlers**: Implemented all 5 advanced filtering commands
- **Database Optimization**: Added indexes for efficient filtering
- **Full-Text Search**: Implemented across descriptions, comments, and tags

### Performance Optimizations
- **Database Indexing**: Optimized indexes for filtering fields
- **Query Optimization**: Efficient SQL queries for complex filters
- **Result Limiting**: Prevents performance issues with large results
- **Caching**: Intelligent caching for repeated queries

### User Experience Enhancements
- **Flexible Parameters**: Optional parameters for easy use
- **Clear Error Messages**: Helpful error messages for troubleshooting
- **Consistent Formatting**: Uniform response formatting
- **Comprehensive Examples**: Detailed examples for all commands

### Security and Validation
- **Input Validation**: Comprehensive parameter validation
- **SQL Injection Prevention**: Parameterized queries
- **Access Control**: Proper permission checking
- **Error Handling**: Graceful error handling without information disclosure

---

*Last updated: June 28, 2025* 