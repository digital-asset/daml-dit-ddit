local snippets = import '../lib/circleci/snippets.jsonnet';
local path = import '../lib/jsonnet/path.jsonnet';

{
  srcPath: path.dirname(std.thisFile),
  circleci: snippets.pythonConfig({
    srcPath: $.srcPath,
    buildDockerImage: false,
  }),
}
