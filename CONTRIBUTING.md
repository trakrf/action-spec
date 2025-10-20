# Contributing to ActionSpec

Thank you for your interest in contributing! This project is a demonstration of YAML-driven infrastructure deployment patterns, and we welcome improvements and feedback.

## Ways to Contribute

### 1. Report Issues
- Found a bug? [Open an issue](https://github.com/trakrf/action-spec/issues)
- Have a feature request? Describe your use case
- Documentation unclear? Let us know what's confusing

### 2. Submit Pull Requests
- Fix bugs or typos
- Add new infrastructure modules
- Improve documentation
- Enhance security or error handling

### 3. Share Your Experience
- How are you using ActionSpec?
- What works well? What doesn't?
- Share your custom infrastructure patterns

## Development Setup

### Prerequisites
- Git
- Bash (Git Bash on Windows, native on macOS/Linux)
- OpenTofu or Terraform
- AWS CLI
- Claude Code installed

**Windows developers**: Use Git Bash or WSL2 for development and testing.

### Testing Your Changes

1. **Clone and test**
   ```bash
   git clone https://github.com/trakrf/action-spec
   cd action-spec
   ```

2. **Validate infrastructure code**
   ```bash
   # Run OpenTofu plan to validate changes
   tofu plan

   # Or with Terraform
   terraform plan
   ```

   See [OpenTofu docs](https://opentofu.org/docs/intro/) for setup and usage.

3. **Test in isolated AWS environment**
   - Use a separate AWS account for testing
   - Enable AWS budget alarms
   - Review all infrastructure changes before applying
   - Clean up resources after testing

## Contribution Guidelines

### Code Style
- **Infrastructure code**: Follow [HashiCorp Style Guide](https://developer.hashicorp.com/terraform/language/style)
- **Shell scripts**: Follow [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
- **Markdown**: Use consistent formatting, clear headings
- **YAML**: Use consistent indentation (2 spaces)

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add S3 bucket module with encryption
fix: correct IAM policy for Lambda execution
docs: clarify AWS prerequisites
chore: update OpenTofu version
```

### Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Keep changes focused and atomic
   - Update documentation as needed
   - Add examples if introducing new features

4. **Test thoroughly**
   - Run `tofu plan` to validate syntax
   - Test on both Unix and Windows if applicable
   - Verify documentation changes render correctly
   - Check for exposed secrets or credentials

5. **Submit PR**
   - Provide clear description of changes
   - Link to related issues
   - Explain the "why" behind your changes
   - Include before/after examples for infrastructure changes

6. **Respond to feedback**
   - Address review comments
   - Be open to suggestions
   - Ask questions if anything is unclear

## Security Considerations

When contributing:
- **Never commit real AWS credentials**
- **Use example files only** (.tfvars.example, .env.local.example)
- **Review all infrastructure changes** before submitting
- **Report security issues** via [GitHub Security Advisories](https://github.com/trakrf/action-spec/security/advisories/new)
- **Follow AWS security best practices**

## Documentation Improvements

Documentation is critical for this project:
- **Clarity**: Use simple, direct language
- **Examples**: Show real-world infrastructure patterns
- **Completeness**: Cover edge cases and security considerations
- **Accuracy**: Keep in sync with code changes

## Questions?

- Open a discussion in [GitHub Issues](https://github.com/trakrf/action-spec/issues)
- Check existing issues for similar questions
- Be patient - this is a demo/portfolio project maintained by volunteers

## Code of Conduct

- Be respectful and constructive
- Focus on the work, not the person
- Welcome newcomers and different perspectives
- Assume good intentions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make ActionSpec better!
