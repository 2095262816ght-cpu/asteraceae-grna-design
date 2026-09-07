# basilisk Windows 补丁：绕过 conda.bat 子进程激活
#
# 问题：basilisk.utils:::.activate_condaenv 用
#   "conda.bat activate && Rscript -e 'socketConnection...'"
# 探测激活后的环境变量。conda activate 会把 crispr 环境的 PATH 条目换掉，
# 子进程 Rscript 找不到本环境 Library/bin 下的 DLL（exit 309 / 0xC0000135），
# 进而触发 "object 'listener' not found"，crisprScore 完全无法打分。
#
# 补丁：把该函数替换为进程内实现——按 conda 激活规则直接把目标环境的
# 标准目录前置到 PATH（效果等价，不开子进程），deactivate 时按 listing 还原。
patch_basilisk <- function() {
  fn <- function(listing, envpath, loc) {
    target <- if (is.null(envpath)) loc else envpath
    subs <- c("", "Library/mingw-w64/bin", "Library/usr/bin",
              "Library/bin", "Scripts", "bin")
    add <- file.path(target, subs)
    add <- normalizePath(add[dir.exists(add)], winslash = "/", mustWork = FALSE)
    old <- Sys.getenv("PATH")
    if (!"PATH" %in% names(listing)) listing[["PATH"]] <- old
    Sys.setenv(PATH = paste(c(add, old), collapse = .Platform$path.sep))
    listing
  }
  utils::assignInNamespace(".activate_condaenv", fn, ns = "basilisk.utils")
  invisible(TRUE)
}
