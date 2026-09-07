# 02: DeepSpCas9 打分（crisprScore），骨架见《分工详案_计算机系.md》A1 节
library(crisprScore)

df <- read.csv("data/hitom_seq30_0909.csv")
df$deepspcas9_score <- getDeepSpCas9Scores(df$seq30)
stopifnot(!any(is.na(df$deepspcas9_score)))
write.csv(df[, c("guide_id", "deepspcas9_score")],
          "results/scores_deepspcas9_0910.csv", row.names = FALSE)
