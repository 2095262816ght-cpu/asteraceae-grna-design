# 03: CRISPRon 打分（crisprScore），骨架见《分工详案_计算机系.md》A1 节
library(crisprScore)

df <- read.csv("data/hitom_seq30_0909.csv")
df$crispron_score <- getCRISPRonScores(df$seq30)
stopifnot(!any(is.na(df$crispron_score)))
write.csv(df[, c("guide_id", "crispron_score")],
          "results/scores_crispron_0911.csv", row.names = FALSE)
