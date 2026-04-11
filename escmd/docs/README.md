# 📚 escmd Documentation

Welcome to the escmd documentation. This directory contains comprehensive guides, references, and configuration information.

## 🗂️ Documentation Structure

### ⚡ **Actions System**
- **[actions.md](commands/actions.md)** - Main actions command documentation
- **[actions-usage-guide.md](guides/actions-usage-guide.md)** - Complete usage examples and best practices
- **[actions-command-reference.md](reference/actions-command-reference.md)** - Command syntax reference
- **[esterm-actions.md](features/esterm-actions.md)** - Actions in interactive terminal mode

### 🖥️ **ESTERM Interactive Terminal**
- **[ESTERM_GUIDE.md](guides/ESTERM_GUIDE.md)** - Complete guide to the interactive terminal
- **[enhanced-prompts.md](features/enhanced-prompts.md)** - Enhanced prompt system features

### 📄 **Template Management**
- **[TEMPLATE_MODIFICATION_GUIDE.md](guides/TEMPLATE_MODIFICATION_GUIDE.md)** - Complete template modification guide
- **[TEMPLATE_MODIFY_QUICK_REFERENCE.md](guides/TEMPLATE_MODIFY_QUICK_REFERENCE.md)** - Quick reference for template operations
- **[TEMPLATE_LIST_OPERATIONS.md](guides/TEMPLATE_LIST_OPERATIONS.md)** - Detailed guide for list operations (append/remove)
- **[template-create-usage.md](guides/template-create-usage.md)** - Template creation guide
- **[template-usage-examples.md](guides/template-usage-examples.md)** - Template usage examples

### 📋 [commands/](commands/)
**Command-Specific Documentation**
- [actions.md](commands/actions.md) - Actions system for automated workflows
- [allocation-management.md](commands/allocation-management.md) - Shard allocation commands
- [cluster-check.md](commands/cluster-check.md) - Health and status monitoring
- [cluster-settings.md](commands/cluster-settings.md) - Cluster settings management
- [dangling-management.md](commands/dangling-management.md) - Dangling indices cleanup
- [exclude-management.md](commands/exclude-management.md) - Node exclusion management
- [health-monitoring.md](commands/health-monitoring.md) - Cluster health workflows
- [ilm-management.md](commands/ilm-management.md) - Index lifecycle management
- [index-operations.md](commands/index-operations.md) - Index management commands
- [node-operations.md](commands/node-operations.md) - Node management operations
- [replica-management.md](commands/replica-management.md) - Replica configuration
- [snapshot-management.md](commands/snapshot-management.md) - Backup and restore

### ⚙️ [configuration/](configuration/)
**Setup and Configuration**
- [installation.md](configuration/installation.md) - Installation instructions
- [cluster-setup.md](configuration/cluster-setup.md) - Cluster configuration (includes **auth profiles**)
- [dual-file-config-guide.md](configuration/dual-file-config-guide.md) - Dual-file mode and **auth profiles** (full reference)
- [password-management.md](configuration/password-management.md) - Password handling and username resolution order

### 🎯 [features/](features/)
**Feature-Specific Documentation**
- [esterm-actions.md](features/esterm-actions.md) - Actions integration in ESTERM
- [enhanced-prompts.md](features/enhanced-prompts.md) - Enhanced prompt system
- [index-metadata.md](features/index-metadata.md) - Index metadata features
- [ILM_BACKUP_RESTORE.md](features/ILM_BACKUP_RESTORE.md) - ILM policy backup and restore feature reference

### 📚 [guides/](guides/)
**User Guides and Tutorials**
- [actions-usage-guide.md](guides/actions-usage-guide.md) - Complete actions system guide
- [ENHANCED_MENU_README.md](guides/ENHANCED_MENU_README.md) - Enhanced menu system
- [ESTERM_GUIDE.md](guides/ESTERM_GUIDE.md) - Interactive terminal guide
- [ILM_S3_INTEGRATION.md](guides/ILM_S3_INTEGRATION.md) - ILM and S3 integration
- [ilm-policy-creation.md](guides/ilm-policy-creation.md) - Complete guide to creating ILM policies
- [QUICKSTART_ILM_BACKUP.md](guides/QUICKSTART_ILM_BACKUP.md) - Quick start guide for ILM policy backup and restore
- [template-create-usage.md](guides/template-create-usage.md) - Template creation usage
- [template-usage-examples.md](guides/template-usage-examples.md) - Template usage examples
- [unfreeze-index-migration.md](guides/unfreeze-index-migration.md) - Unfreeze index migration guide

### 🎨 [themes/](themes/)
**Universal Theme System Documentation**
- [README.md](themes/README.md) - Theme documentation index
- [CUSTOM_THEMES_GUIDE.md](themes/CUSTOM_THEMES_GUIDE.md) - Creating custom themes
- [UNIVERSAL_THEME_SYSTEM_GUIDE.md](themes/UNIVERSAL_THEME_SYSTEM_GUIDE.md) - System implementation
- [THEME_GUIDE.md](themes/THEME_GUIDE.md) - Basic usage guide
- [ESTERM_THEMES_README.md](themes/ESTERM_THEMES_README.md) - ESTERM interactive terminal themes
- [style-migration-guide.md](themes/style-migration-guide.md) - Style migration

### 📖 [reference/](reference/)
**Reference Information**
- [actions-command-reference.md](reference/actions-command-reference.md) - Actions command syntax reference
- [changelog.md](reference/changelog.md) - Version history and changes
- [troubleshooting.md](reference/troubleshooting.md) - Common issues and solutions
- [testing.md](reference/testing.md) - Testing documentation
- [ilm-policy-creation-quick-reference.md](reference/ilm-policy-creation-quick-reference.md) - ILM policy creation quick reference

### 📦 [releases/](releases/)
**Release Notes and Version History**
- [RELEASE_3.7.0.md](releases/RELEASE_3.7.0.md) - v3.7.0 release summary (environment-specific metrics)
- [RELEASE_3.7.1.md](releases/RELEASE_3.7.1.md) - v3.7.1 release summary (enhanced repository verification errors)
- [RELEASE_3.7.2.md](releases/RELEASE_3.7.2.md) - v3.7.2 release notes (ILM policy backup and restore)
- [HOTFIX_3.7.2.1.md](releases/HOTFIX_3.7.2.1.md) - v3.7.2.1 hotfix (ILM remove-policy fixes for data stream indices)
- [RELEASE_3.8.5.md](releases/RELEASE_3.8.5.md) - v3.8.5 release notes (auth profiles)
- [RELEASE_3.8.4.md](releases/RELEASE_3.8.4.md) - v3.8.4 release notes (emoji/terminal table alignment fix)
- [VERSION_3.7.2_FILES_CHANGED.md](releases/VERSION_3.7.2_FILES_CHANGED.md) - Detailed file change manifest for v3.7.2
- [VERSION_UPDATE_SUMMARY.md](releases/VERSION_UPDATE_SUMMARY.md) - Consolidated v3.7.2 update summary

### 🔄 [workflows/](workflows/)
**Operational Workflows**
- [dangling-cleanup.md](workflows/dangling-cleanup.md) - Dangling indices cleanup process
- [monitoring-workflows.md](workflows/monitoring-workflows.md) - Monitoring best practices

### 🛠️ [development/](development/)
**Development and Enhancement Documentation**
- [action-integration-complete.md](development/action-integration-complete.md) - Action system integration completion
- [action-output-improvements-summary.md](development/action-output-improvements-summary.md) - Action output improvements
- [actions-output-enhancements.md](development/actions-output-enhancements.md) - Action output enhancements details
- [alphabetical-sorting-changes.md](development/alphabetical-sorting-changes.md) - Alphabetical sorting implementation
- [connection-fix-plans.md](development/connection-fix-plans.md) - Connection fix implementation plans
- [performance-improvements.md](development/performance-improvements.md) - Performance optimization summary
- [template-modification-complete.md](development/template-modification-complete.md) - Template modification completion
- [template-modification-implementation.md](development/template-modification-implementation.md) - Template modification implementation
- [unfreeze-migration-complete.md](development/unfreeze-migration-complete.md) - Unfreeze index migration completion
- [ilm-policy-creation-feature-summary.md](development/ilm-policy-creation-feature-summary.md) - ILM policy creation feature summary
- And many more development summaries and implementation details...

## 🚀 Quick Links

- **[⚡ Actions System](commands/actions.md)** - Powerful automation workflows for common tasks
- **[🖥️ ESTERM Interactive Terminal](guides/ESTERM_GUIDE.md)** - Start here for the interactive terminal experience
- **[📄 Template Management](guides/TEMPLATE_MODIFICATION_GUIDE.md)** - Complete guide to template modifications with list operations
- **[🆕 ILM Policy Creation](guides/ilm-policy-creation.md)** - Create and manage Index Lifecycle Management policies
- **[📋 Latest Changes](reference/changelog.md)** - See what's new (e.g. v3.8.5 auth profiles)
- **[📦 Release Notes](releases/)** - Full version history and release details
- **[🎨 Theme System](themes/)** - Complete theming documentation
- **[⚙️ Installation](configuration/installation.md)** - Get started quickly
- **[🔍 Troubleshooting](reference/troubleshooting.md)** - Solve common issues

## 🎯 Getting Started

1. **Installation:** Follow the [installation guide](configuration/installation.md)
2. **Configuration:** Set up your [cluster configuration](configuration/cluster-setup.md)
3. **Interactive Terminal:** Try the [ESTERM interactive terminal](guides/ESTERM_GUIDE.md) for the best experience
4. **Actions System:** Learn the [actions system](commands/actions.md) for automated workflows and common tasks
5. **Template Management:** Learn [template modifications](guides/TEMPLATE_MODIFICATION_GUIDE.md) including list operations for host exclusions
6. **ILM Policies:** Learn to [create ILM policies](guides/ilm-policy-creation.md) for data lifecycle management; see the [ILM backup & restore quick start](guides/QUICKSTART_ILM_BACKUP.md) for maintenance workflows
7. **Themes:** Explore the [theme system](themes/) for customization
8. **Commands:** Browse [command documentation](commands/) for specific operations
9. **Workflows:** Check [operational workflows](workflows/) for best practices

## 🆕 Latest Features

### Auth profiles (v3.8.5)

- **Portable server lists**: Shared **`elastic_servers.yml`** can use **`auth_profile`** instead of embedding **`elastic_username`** per person.
- **Local mappings**: Define **`auth_profiles`** in **`escmd.yml`** (dual-file) or **`ESCMD_MAIN_CONFIG`** so each operator maps profile names to real accounts.
- **Docs**: [dual-file-config-guide.md](configuration/dual-file-config-guide.md#auth-profiles) — [changelog](reference/changelog.md)

### Actions System for Workflow Automation
The escmd utility now includes a powerful actions system for automating complex workflows:

- **Reusable Workflows**: Define sequences of commands that can be executed together
- **Parameterized Operations**: Use variables to customize behavior across environments
- **Safety Features**: Built-in dry-run mode and confirmation prompts for destructive operations
- **Multiple Output Modes**: Standard, quiet, summary-only, and compact modes for different use cases
- **ESterm Integration**: Full support in interactive terminal mode with context awareness

**Quick Start**: `./escmd.py action list` and `./escmd.py action run health-check`  
**Full Guide**: [Actions Usage Guide](guides/actions-usage-guide.md)  
**Command Reference**: [Actions Command Reference](reference/actions-command-reference.md)

### Template Management with List Operations
The escmd utility supports comprehensive template modification with intelligent list operations:

- **Append/Remove Operations**: Add or remove values from comma-separated lists (host exclusions, etc.)
- **Safe Modifications**: Automatic backups and dry-run mode for testing changes
- **Duplicate Prevention**: Smart handling of list values to avoid duplicates
- **Multiple Template Types**: Component, composable, and legacy template support

**Quick Start**: `./escmd.py template-modify manual_template -f template.settings.index.routing.allocation.exclude._name -o append -v "host1-*"`  
**Full Guide**: [Template Modification Guide](guides/TEMPLATE_MODIFICATION_GUIDE.md)

### ILM Policy Creation
The escmd utility now supports comprehensive ILM policy creation directly from the command line:

- **Multiple Input Methods**: JSON files, inline JSON, or file flags
- **Rich Output**: Beautiful themed displays and JSON format for automation  
- **Complete Documentation**: Full guides, quick reference, and examples
- **Integrated Help**: Available via `./escmd.py help ilm`

**Quick Start**: `./escmd.py -l cluster ilm create-policy my-policy policy.json`  
**Full Guide**: [ILM Policy Creation Guide](guides/ilm-policy-creation.md)

---

*For the main project README, see the root directory file.*
